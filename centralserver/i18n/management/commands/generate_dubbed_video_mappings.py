"""
Command to import mappings from spreadsheet, convert to a json dictionary.
"""
import copy
import json
import os
from optparse import make_option

from django.conf import settings; logging = settings.LOG
from django.core.management.base import BaseCommand

from ... import DUBBED_VIDEOS_MAPPING_FILEPATH, get_dubbed_video_map
from fle_utils.general import ensure_dir
from kalite.i18n import get_code2lang_map


def dubbed_videos_from_api():
    """Create a dictionary with the language's ka_name as key, with the
    value another dictionary mapping a youtube id to another youtube id for its dubbed version.

    e.g.

    {
    "arabic": {
        "-6Fu2T_RSGM": "3tsYDMfSxCE",
        "-7kSDHFXwZ4": "GZtjWqGH_kk",
        "-9gl_HlsatI": "AxtRhoha8iE",
        "-FtlH4svqx4": "y0UK0zD9Lsg",
    ...
    """
    pass


class Command(BaseCommand):
    help = "Make a dictionary of english video=>dubbed video mappings, from the online Google Docs spreadsheet."

    option_list = BaseCommand.option_list + (
        make_option('--force',
                    action='store_true',
                    dest='force',
                    default=False,
                    help='Force reload of spreadsheet'),
        make_option('--max-age',
                    action='store',
                    dest='max_cache_age',
                    default=7.0,
                    help='Max # of days to use cached database file.'),
        make_option('--cache-filepath',
                    action='store',
                    dest='cache_filepath',
                    default=None,
                    help='Location to load/store a cached dubbings file'),
    )

    def handle(self, *args, **options):


        old_map = os.path.exists(DUBBED_VIDEOS_MAPPING_FILEPATH) and copy.deepcopy(get_dubbed_video_map()) or {}  # for comparison purposes

        # Use cached data to generate the video map


        # Remove any dummy (empty) entries, as this breaks everything on the client
        if "" in raw_map:
            del raw_map[""]

        for lang_code in settings.DUBBED_LANGUAGES_FETCHED_IN_API:
            logging.info("Updating {} from the API".format(lang_code))
            map_from_api = dubbed_video_data_from_api(lang_code)
            lang_metadata = get_code2lang_map(lang_code)
            lang_ka_name = lang_metadata["ka_name"]
            raw_map[lang_ka_name].update(map_from_api)

        # Now we've built the map.  Save it.
        ensure_dir(os.path.dirname(DUBBED_VIDEOS_MAPPING_FILEPATH))
        logging.info("Saving data to %s" % DUBBED_VIDEOS_MAPPING_FILEPATH)
        with open(DUBBED_VIDEOS_MAPPING_FILEPATH, "w") as fp:
            json.dump(raw_map, fp)

        new_map = get_dubbed_video_map(reload=True)

        # Now tell the user about what changed.
        added_languages = set(new_map.keys()) - set(old_map.keys())
        removed_languages = set(old_map.keys()) - set(new_map.keys())
        if added_languages or removed_languages:
            logging.info("*** Added support for %2d languages; removed support for %2d languages. ***" % (len(added_languages), len(removed_languages)))

        for lang_code in sorted(list(set(new_map.keys()).union(set(old_map.keys())))):
            added_videos = set(new_map.get(lang_code, {}).keys()) - set(old_map.get(lang_code, {}).keys())
            removed_videos = set(old_map.get(lang_code, {}).keys()) - set(new_map.get(lang_code, {}).keys())
            shared_keys = set(new_map.get(lang_code, {}).keys()).intersection(set(old_map.get(lang_code, {}).keys()))
            changed_videos = [vid for vid in shared_keys if old_map.get(lang_code, {})[vid] != new_map.get(lang_code, {})[vid]]
            logging.info("\t%5s: Added %d videos, removed %3d videos, changed %3d videos." % (lang_code, len(added_videos), len(removed_videos), len(changed_videos)))

        logging.info("Done.")
