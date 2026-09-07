"""GPU worker entry points (contract §7, §10).

``python -m worker.aws_worker`` consumes the SQS job queue on ECS, ``worker.modal_app``
is deployed with ``modal deploy`` and ``python -m worker.runpod_handler`` serves RunPod
serverless requests. All three share :mod:`worker.common`, which downloads the input,
runs the pipeline selected by ``SNAPPLAY_PIPELINE``, uploads the stems and MIDI to
``jobs/<user_id>/<job_id>/`` and records the outcome through the job service.
"""
