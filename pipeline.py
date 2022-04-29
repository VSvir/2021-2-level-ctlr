"""
Pipeline for text processing implementation
"""
import re
from pathlib import Path

import pymorphy2
from pymystem3 import Mystem

from constants import ASSETS_PATH
from core_utils.article import Article, ArtifactType


class EmptyDirectoryError(Exception):
    """
    No data to process
    """


class InconsistentDatasetError(Exception):
    """
    Corrupt data:
        - numeration is expected to start from 1 and to be continuous
        - a number of text files must be equal to the number of meta files
        - text files must not be empty
    """


class MorphologicalToken:
    """
    Stores language params for each processed token
    """

    def __init__(self, original_word):
        self.original_word = original_word
        self.normalized_form = ''
        self.tags_mystem = ''
        self.tags_pymorphy = ''

    def get_cleaned(self):
        """
        Returns lowercased original form of a token
        """
        return self.original_word.lower()

    def get_single_tagged(self):
        """
        Returns normalized lemma with MyStem tags
        """
        return f'{self.normalized_form}<{self.tags_mystem}>'

    def get_multiple_tagged(self):
        """
        Returns normalized lemma with PyMorphy tags
        """
        return f'{self.normalized_form}<{self.tags_mystem}>({self.tags_pymorphy})'


class CorpusManager:
    """
    Works with articles and stores them
    """

    def __init__(self, path_to_raw_txt_data: str):
        self.path = Path(path_to_raw_txt_data)
        self._storage = {}
        self._scan_dataset()

    def _scan_dataset(self):
        """
        Register each dataset entry
        """
        dataset = list(self.path.glob('*_raw.txt'))
        dataset.sort(key=self._extract_file_id)
        for file in dataset:
            file_id = self._extract_file_id(file)
            self._storage[file_id] = Article(url=None, article_id=file_id)

    def _extract_file_id(self, file):
        pattern = re.compile(r'\d+')
        return int(pattern.match(file.stem).group())

    def get_articles(self):
        """
        Returns storage params
        """
        return self._storage


class TextProcessingPipeline:
    """
    Process articles from corpus manager
    """

    def __init__(self, corpus_manager: CorpusManager):
        self.corpus_manager = corpus_manager

    def run(self):
        """
        Runs pipeline process scenario
        """
        for article in self.corpus_manager.get_articles().values():
            tokens = self._process(article.get_raw_text())
            tokenized_text = ' '.join(tokens[0])
            tokenized_mystem_text = ' '.join(tokens[1])
            tokenized_double_tagged_text = ' '.join(tokens[2])

            article.save_as(text=tokenized_text, kind=ArtifactType.cleaned)
            article.save_as(text=tokenized_mystem_text, kind=ArtifactType.single_tagged)
            article.save_as(text=tokenized_double_tagged_text, kind=ArtifactType.multiple_tagged)

    def _process(self, raw_text: str):
        """
        Processes each token and creates MorphToken class instance
        """
        tokens = []
        cleaned_tokens = []
        mystem_tokens = []
        multiple_tagged_tokens = []

        transferences_and_footers = re.compile(r'(-\n)|(\d+\s+[^\n]([А-Я]\.)+\s[А-Яа-я]+\s\n)'
                                               r'|(([А-ЯёЁ]([А-Яа-яёЁ\-]+\s)+)\s+\d\s\n)|(\n)')

        preprocessed_text = transferences_and_footers.sub('', raw_text)

        result = Mystem().analyze(preprocessed_text)
        morph = pymorphy2.MorphAnalyzer()

        for processed_word in result:
            if processed_word.get('analysis') is not None and processed_word.get('analysis'):
                mystem_token = MorphologicalToken(processed_word['text'])
                mystem_token.normalized_form = processed_word['analysis'][0]['lex']
                mystem_token.tags_mystem = processed_word['analysis'][0]['gr']

                mystem_token.tags_pymorphy = morph.parse(mystem_token.original_word)[0].tag

                cleaned_tokens.append(MorphologicalToken(mystem_token.original_word).get_cleaned())
                mystem_tokens.append(mystem_token.get_single_tagged())
                multiple_tagged_tokens.append(mystem_token.get_multiple_tagged())

        tokens.append(cleaned_tokens)
        tokens.append(mystem_tokens)
        tokens.append(multiple_tagged_tokens)
        return tokens


def validate_dataset(path_to_validate):
    """
    Validates folder with assets
    """
    if isinstance(path_to_validate, str):
        path_to_validate = Path(path_to_validate)
    if not path_to_validate.exists():
        raise FileNotFoundError(f'NO {ASSETS_PATH} FOLDER FOUND.')
    if not path_to_validate.is_dir():
        raise NotADirectoryError(f'{ASSETS_PATH} IS NOT A FOLDER.')
    if not list(path_to_validate.glob('**/*')):
        raise EmptyDirectoryError(f'{ASSETS_PATH} FOLDER IS EMPTY.')
    if check_dataset_numeration(path_to_validate) == -1:
        raise InconsistentDatasetError('ERROR. INCORRECT DATASET.')
    if check_txt_files(path_to_validate) == -1:
        raise InconsistentDatasetError('ERROR. EMPTY RAW TXT FILES FOUND.')


def check_dataset_numeration(dataset_path):
    """
    Checks that the dataset is valid
    """
    files_to_check = ['_raw', '_meta']
    files = {
        '.json': [],
        '.txt': [],
        '.pdf': []
    }
    sorted_files = {}
    pattern = re.compile(r'(?P<file_id>\d+)(?P<file_name>_\w+)')

    for file in list(dataset_path.glob('*')):
        if pattern.match(file.stem).group('file_name') in files_to_check:
            files.get(file.suffix).append(int(pattern.match(file.stem).group('file_id')))

    for files_suffix, ids_list in files.items():
        sorted_files[files_suffix] = sorted(ids_list)

    for files_suffix, sorted_ids_list in sorted_files.items():
        for file_number in range(1, len(sorted_ids_list) + 1):
            if sorted_ids_list[file_number - 1] != file_number:
                print(f'Missing file № {file_number} with {files_suffix} suffix')
                return -1

    if files.get('.json') != files.get('.txt'):
        return -1
    return 0


def check_txt_files(dataset_path):
    for file in list(dataset_path.glob('*_raw.txt')):
        if file.stat().st_size == 0:
            return -1
    return 0


def main():
    print(f'STARTING PROGRAM...\nFOUND {len(list(ASSETS_PATH.glob("*_raw.txt")))} FILES.\n'
          f'VALIDATING DATASET...')
    validate_dataset(ASSETS_PATH)
    print('DATASET IS CORRECT.\nCREATING CORPUS MANAGER ABSTRACTION...')
    corpus_manager = CorpusManager(ASSETS_PATH)
    print('DONE.\nCREATING PIPELINE INSTANCE...')
    pipe = TextProcessingPipeline(corpus_manager)
    print('DONE.\nRUNNING TEXT PROCESSING PIPELINE ON COLLECTED FILES...')
    pipe.run()
    print('DONE.\nPROGRAM FINISHED.')


if __name__ == "__main__":
    main()
