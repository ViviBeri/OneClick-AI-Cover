# RVC retrieval index files

The pinned RVC CLI accepts an explicit added index through --index and applies it
with --index-rate (0.0 to 1.0). Index files are optional: conversion continues
without retrieval when no index is selected.

## Import and use

1. Generate the added index for the same voice model in the upstream RVC
   training workflow.
2. Open **Import RVC Index** and select the resulting .index file.
3. In **Generate Cover**, expand **RVC retrieval index (optional)**.
4. Select the matching index and start with an index strength around 0.5–0.75.
5. Compare the result by listening. The best setting depends on the model,
   source vocal, and index quality.

Indexes are stored locally under models/indices/. They are not downloaded
automatically and are not uploaded. The app checks the extension, non-empty
file size, and local path; it cannot prove that an index belongs to a
particular checkpoint. Selecting an index built for another voice model can
degrade output or cause inference errors.

The default index strength is 0.0 when no index is selected. A selected index
is passed to the pinned RVC CLI only when its strength is greater than zero.
