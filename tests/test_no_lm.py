"""Il livello letterale non deve MAI usare un language model (kenlm / ProcessorWithLM)."""
from app.pipeline import literal


def test_processor_is_plain_ctc():
    literal.assert_no_language_model()


def test_processor_class_and_no_decoder():
    processor, _ = literal._load()
    assert processor.__class__.__name__ == "Wav2Vec2Processor"
    # Wav2Vec2ProcessorWithLM espone un .decoder (pyctcdecode/kenlm): qui NON deve esistere.
    assert getattr(processor, "decoder", None) is None
