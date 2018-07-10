# -*- coding: utf-8 -*-
from pytest import fixture

from storyscript.story import Story


@fixture
def story():
    return Story('story')


def test_story_init(story):
    assert story.story == 'story'


def test_story_from_file(patch):
    patch.init(Story)
    result = Story.from_file('hello.story')
    Story.__init__.assert_called_with('hello.story', 'file')
    assert isinstance(result, Story)


def test_story_from_stream(patch):
    patch.init(Story)
    result = Story.from_stream('stream')
    Story.__init__.assert_called_with('stream', 'stream')
    assert isinstance(result, Story)


