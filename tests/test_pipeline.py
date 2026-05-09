import pytest
from shorts.pipeline import Pipeline

def test_pipeline_sequence():
    pipeline = Pipeline()
    assert pipeline.STEPS == [
        "idea_gen",
        "tts",
        "bgm_mix",
        "scenes",
        "clips",
        "render",
        "thumbnail",
        "upload_yt"
    ]

def test_get_runnable_steps_empty():
    pipeline = Pipeline()
    # Initially, only the first step should be runnable
    assert pipeline.get_runnable_steps(set()) == ["idea_gen"]

def test_get_runnable_steps_partial():
    pipeline = Pipeline()
    completed = {"idea_gen", "tts"}
    assert pipeline.get_runnable_steps(completed) == ["bgm_mix"]

def test_get_runnable_steps_complete():
    pipeline = Pipeline()
    completed = {
        "idea_gen", "tts", "bgm_mix", "scenes", 
        "clips", "render", "thumbnail", "upload_yt"
    }
    assert pipeline.get_runnable_steps(completed) == []

def test_is_complete():
    pipeline = Pipeline()
    assert not pipeline.is_complete(set())
    completed = {
        "idea_gen", "tts", "bgm_mix", "scenes", 
        "clips", "render", "thumbnail", "upload_yt"
    }
    assert pipeline.is_complete(completed)

def test_get_runnable_steps_out_of_order():
    pipeline = Pipeline()
    # If a middle step is done but predecessors aren't, 
    # the first missing predecessor should be returned.
    completed = {"tts"} # idea_gen missing
    assert pipeline.get_runnable_steps(completed) == ["idea_gen"]
