# CAD Plugin Feature Summary

- First-launch API key setup with later settings-based reconfiguration.
- Secure API key storage when OS-backed credential storage is available.
- Chat-style workflow for creating new CAD jobs from text prompts.
- Reference image attachment support for creation and iteration.
- Background job polling with status updates and API-recommended poll delays.
- Automatic detection and listing of generated STEP artifacts.
- Download and import/open actions for generated CAD results.
- Default auto-open behavior for the top-level completed assembly/result.
- Review/Iterate mode control.
- Review mode uses the dedicated synchronous review assistant endpoint.
- Iterate mode sends follow-up CAD modification requests to the active job.
- New Chat action to start a fresh job after a result is complete.
- Recent Jobs list loaded from the API, including web and API-created jobs.
- Searchable, collapsible recent-job browser.
- Restore public chat history and latest artifacts from a recent job.
- Reduced transcript noise with distinct user, assistant, system, and error styling.
