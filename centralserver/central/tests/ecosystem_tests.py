from django.contrib.auth.models import User
from django.test import LiveServerTestCase

from centralserver.central.models import Organization
from securesync.tests import SecuresyncTestCase
from securesync.devices.models import Device, Zone

from .utils.distributed_server_factory import DistributedServer


class SameVersionTests(SecuresyncTestCase, LiveServerTestCase):

    def setUp(self):
        # TODO (aron): move this entire thing into its own mixins
        Device.own_device = None
        self.setUp_fake_device()

        self.user = User.objects.create(username='test_user',
                                        password='invalid_password')
        self.test_org = Organization.objects.create(name='test_org',
                                                    owner=self.user)
        self.test_zone = Zone.objects.create(name='test_zone')
        self.test_zone.organization_set.add(self.test_org)
        self.test_zone.save()

    def test_can_run_on_distributed_server(self):
        with DistributedServer(CENTRAL_SERVER_HOST=self.live_server_url) as d1:
            d1.call_command('validate')
            _stdout, stderr = d1.wait()
            # the command shouldn't have printed anything to stderr
            self.assertFalse(stderr)

    def test_can_instantiate_two_distributed_servers(self):
        settings = {'CENTRAL_SERVER_HOST': self.live_server_url}

        with DistributedServer(**settings) as d1, DistributedServer(**settings) as d2:
            d1.call_command('validate')
            d2.call_command('validate')

            d1.wait()
            d2.wait()
