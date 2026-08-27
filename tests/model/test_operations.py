from kash.model.operations_model import Input, Operation
from kash.model.paths_model import StorePath


def test_operation_identity_canonicalizes_option_order() -> None:
    input_item = Input(StorePath("resources/watch.resource.yml"), "sha1:fixture")
    declared = Operation(
        action_name="transcribe",
        arguments=[input_item],
        options={
            "language": "en",
            "transcription_model": "nova-3",
            "diarize_model": "latest",
            "key_terms": "Hotel Check In",
        },
    )
    reloaded = Operation.from_dict(
        {
            "action_name": "transcribe",
            "arguments": [input_item.parseable_str()],
            "options": {
                "diarize_model": "latest",
                "key_terms": "Hotel Check In",
                "language": "en",
                "transcription_model": "nova-3",
            },
        }
    )

    assert declared.as_str() == reloaded.as_str()
