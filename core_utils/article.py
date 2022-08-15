"""
Article implementation
"""
import json
import datetime

from constants import ASSETS_PATH


class ArtifactType:
    cleaned = 'cleaned'
    single_tagged_mystem = 'single_tagged (mystem)'
    single_tagged_pymorphy = 'single_tagged (pymorphy)'
    multiple_tagged = 'multiple_tagged'


def date_from_meta(date_txt):
    """
    Converts text date to datetime object
    """
    return datetime.datetime.strptime(date_txt, "%Y-%m-%d %H:%M:%S")


class Article:
    """
    Article class implementation.
    Stores article metadata and knows how to work with articles
    """

    def __init__(self, url, article_id):
        self.url = url
        self.article_id = article_id

        self.title = ''
        self.date = None
        self.author = ''
        self.topics = []
        self.text = ''

        meta_file = self.get_meta_file_path()
        if meta_file.exists():
            self.from_meta_json(meta_file)

    def save_raw(self):
        """
        Saves raw text and article meta data
        """
        article_meta_name = "{}_meta.json".format(self.article_id)

        with open(self.get_raw_text_path(), 'w', encoding='utf-8') as file:
            file.write(self.text)

        if self.author:
            with (ASSETS_PATH / article_meta_name).open("w", encoding='utf-8') as file:
                json.dump(self._get_meta(), file, sort_keys=False,
                          indent=4, ensure_ascii=False, separators=(',', ': '))

    def from_meta_json(self, json_path: str):
        """
        Loads meta.json file and writes its data
        """
        with open(json_path, encoding='utf-8') as meta_file:
            meta = json.load(meta_file)

        self.url = meta.get('url', None)
        self.title = meta.get('title', '')
        self.date = date_from_meta(meta.get('date', None))
        self.author = meta.get('author', None)
        self.topics = meta.get('topics', None)

        # intentionally leave it empty
        self.text = None

    def get_raw_text(self):
        """
        Gets a raw text for requested article
        """
        with open(self.get_raw_text_path(), encoding='utf-8') as file:
            return file.read()

    def save_as(self, text: str, kind: str) -> None:
        """
        Creates a file with a given text and corresponding name
        text: a string object to write in a created file
        kind: variant of a file -- cleaned, single-tagged with mystem or pymorphy tags
        or multiple-tagged
        """
        with open(self.get_file_path(kind), 'w', encoding='utf-8') as file:
            file.write(text)

    def _get_meta(self):
        """
        Gets all article params
        """
        return {
            'id': self.article_id,
            'url': self.url,
            'title': self.title,
            'date': self._date_to_text(),
            'author': self.author,
            'topics': self.topics
        }

    def _date_to_text(self):
        """
        Converts datetime object to text
        """
        return self.date.strftime("%Y-%m-%d %H:%M:%S")

    def get_raw_text_path(self):
        """
        Returns path for requested raw article
        """
        article_txt_name = "{}_raw.txt".format(self.article_id)
        return ASSETS_PATH / article_txt_name

    def get_meta_file_path(self):
        """
        Returns path for requested raw article
        """
        meta_file_name = "{}_meta.json".format(self.article_id)
        return ASSETS_PATH / meta_file_name

    def get_file_path(self, kind: str) -> str:
        """
        Returns a proper filepath for an Article instance
        kind: variant of a file -- cleaned, single-tagged with mystem or pymorphy tags
        or multiple-tagged
        """
        supported_kinds = (
            ArtifactType.cleaned,
            ArtifactType.single_tagged_mystem,
            ArtifactType.single_tagged_pymorphy,
            ArtifactType.multiple_tagged
        )

        if kind not in supported_kinds:
            accepted_types = ', '.join(supported_kinds)
            raise ValueError(f'Kind of a file to save must be '
                             f'one of the following: {accepted_types}, '
                             f'received {kind}')

        article_txt_name = "{}_{}.txt".format(self.article_id, kind)

        return ASSETS_PATH / article_txt_name
