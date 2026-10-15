# Keep scene credits with prepared targets

The new native cache initially retained the publisher's attribution string but
referenced permissions.txt in the acquisition directory. The preparer now
requires, verifies and copies that file beside the prepared targets so the
per-scene credits travel with the cache. The actual cache was resumed; its
manifest SHA256 and all image contents remain unchanged. Running V20/V21 data
and resume identities are unaffected. The focused 13 native-data tests and Ruff
pass, including copied-credit content and repeat preparation checks.
