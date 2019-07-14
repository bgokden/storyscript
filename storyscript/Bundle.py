# -*- coding: utf-8 -*-
import os
import subprocess

from .Features import Features
from .Story import Story
from .parser import Parser


class Bundle:
    """
    Bundles all stories that must be compiled together.
    """

    def __init__(self, story_files=None, features=None):
        self.stories = {}
        if isinstance(features, Features):
            self.features = features
        else:
            self.features = Features(features)
        if story_files is None:
            story_files = {}
        self.story_files = story_files

    @staticmethod
    def gitignores():
        """
        Get the list of files ignored by git
        """
        command = ['git', 'ls-files', '--others', '--ignored',
                   '--exclude-standard']
        p = subprocess.run(command,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL,
                           encoding='utf8')
        if p.returncode != 0:
            return []
        return p.stdout.split('\n')

    @staticmethod
    def ignores(path):
        ignores = []
        if os.path.isdir(path):
            for root, subdirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.story'):
                        story = os.path.relpath(os.path.join(root, file))
                        ignores.append(story)
            return ignores
        return [os.path.relpath(path)]

    @staticmethod
    def filter_path(root, filename, ignores):
        if filename.endswith('.story'):
            path = os.path.relpath(os.path.join(root, filename))
            if path not in ignores:
                return path
        return None

    @classmethod
    def parse_directory(cls, directory, ignored_path=None):
        """
        Parse a directory to find stories.
        """
        paths = []
        ignores = cls.gitignores()
        if ignored_path:
            ignores = ignores + cls.ignores(ignored_path)
        for root, subdirs, files in os.walk(directory):
            for file in files:
                path = cls.filter_path(root, file, ignores)
                if path:
                    paths.append(path)
        return paths

    @classmethod
    def from_path(cls, path, ignored_path=None, features=None):
        """
        Load a bundle of stories from the filesystem.
        If a directory is given. all `.story` files in the directory will be
        loaded.
        """
        bundle = Bundle(features=features)
        if os.path.isdir(path):
            for story in cls.parse_directory(path, ignored_path=ignored_path):
                bundle.load_story(story)
            return bundle
        bundle.load_story(path)
        return bundle

    def load_story(self, path):
        """
        Reads a story file and adds it to the loaded stories
        """
        if path not in self.story_files:
            self.story_files[path] = Story.read(path)
        return Story(self.story_files[path], features=self.features, path=path)

    def find_stories(self):
        """
        Finds bundle stories.
        """
        return list(self.story_files.keys())

    def services(self):
        services = []
        for storypath, story in self.stories.items():
            services += story['services']
        services = list(set(services))
        services.sort()
        return services

    def parser(self, ebnf):
        if ebnf is not None:
            return Parser(ebnf=ebnf)
        return None

    def parse(self, stories, parser, lower):
        """
        Parse stories.
        """
        for storypath in stories:
            story = self.load_story(storypath)
            story.parse(parser=parser, lower=lower)
            self.stories[storypath] = story.tree

    def compile(self, stories, parser):
        """
        Reads, parses and compiles the story.
        """
        for storypath in stories:
            story = self.load_story(storypath)
            story.parse(parser=parser)
            story.compile()
            self.stories[storypath] = story.compiled

    def bundle(self, ebnf=None):
        """
        Makes the bundle
        """
        entrypoint = self.find_stories()
        parser = self.parser(ebnf)
        self.compile(entrypoint, parser=parser)
        return {'stories': self.stories, 'services': self.services(),
                'entrypoint': entrypoint}

    def bundle_trees(self, ebnf=None, lower=False):
        """
        Makes a bundle of syntax trees
        """
        parser = self.parser(ebnf)
        self.parse(self.find_stories(), parser=parser, lower=lower)
        return self.stories

    def lex(self, ebnf=None):
        """
        Lexes the bundle
        """
        stories = self.find_stories()
        parser = self.parser(ebnf)
        results = {}
        for story in stories:
            results[story] = Story.from_file(story, features=self.features) \
                                  .lex(parser=parser)
        return results
