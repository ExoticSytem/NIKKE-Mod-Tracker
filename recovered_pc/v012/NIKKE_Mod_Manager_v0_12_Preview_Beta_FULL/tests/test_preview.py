import struct

from src.preview import PreviewError, decrypt_nkab


def test_non_nkab_is_passed_through():
    raw = b'UnityFS' + b'abc123'
    plain, version = decrypt_nkab(raw)
    assert plain == raw
    assert version is None


def test_unknown_nkab_version_is_reported():
    raw = b'NKAB' + struct.pack('<I', 999) + b'0' * 64
    try:
        decrypt_nkab(raw)
    except PreviewError as exc:
        assert '999' in str(exc)
    else:
        raise AssertionError('Expected PreviewError')
