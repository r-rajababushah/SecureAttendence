import json
import tempfile
import unittest
from pathlib import Path

from attendance_store import AttendanceStore, sample_records, validate_status
from auth import (
    authenticate,
    create_instructor_account,
    get_account_role,
    has_permission,
    list_accounts,
    register_admin,
    register_instructor,
)
from crypto_utils import create_keys, decrypt_bytes, encrypt_bytes, load_key, verify_envelope


class SecureAttendanceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.secrets_dir = self.root / "secrets"
        create_keys(self.secrets_dir)
        self.enc_key = load_key(self.secrets_dir / "encryption.key")
        self.mac_key = load_key(self.secrets_dir / "hmac.key")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_correct_and_incorrect_password(self):
        auth_file = self.secrets_dir / "instructor.json"
        register_instructor(auth_file, "mentor", "a long example password")
        self.assertTrue(authenticate(auth_file, "mentor", "a long example password"))
        self.assertFalse(authenticate(auth_file, "mentor", "wrong password"))

    def test_plaintext_password_is_not_stored(self):
        auth_file = self.secrets_dir / "instructor.json"
        password = "this is a secret password"
        register_instructor(auth_file, "mentor", password)
        stored = auth_file.read_text(encoding="utf-8")
        self.assertNotIn(password, stored)
        self.assertIn("argon2id", stored)

    def test_first_account_is_admin_and_can_create_instructor(self):
        auth_file = self.secrets_dir / "instructor.json"
        register_admin(auth_file, "lead", "a long admin password")
        create_instructor_account(auth_file, "lead", "teacher2", "a long teacher password")

        self.assertEqual(get_account_role(auth_file, "lead"), "admin")
        self.assertEqual(get_account_role(auth_file, "teacher2"), "instructor")
        self.assertTrue(authenticate(auth_file, "teacher2", "a long teacher password"))
        self.assertTrue(has_permission("admin", "accounts:create"))
        self.assertFalse(has_permission("instructor", "accounts:create"))
        self.assertTrue(has_permission("instructor", "attendance:mark"))
        self.assertEqual([user["role"] for user in list_accounts(auth_file)], ["admin", "instructor"])

    def test_instructor_cannot_create_accounts_and_duplicate_names_are_rejected(self):
        auth_file = self.secrets_dir / "instructor.json"
        register_admin(auth_file, "lead", "a long admin password")
        create_instructor_account(auth_file, "lead", "teacher2", "a long teacher password")

        with self.assertRaises(PermissionError):
            create_instructor_account(auth_file, "teacher2", "teacher3", "a long teacher password")
        with self.assertRaises(ValueError):
            create_instructor_account(auth_file, "lead", "TEACHER2", "another long password")

    def test_legacy_single_account_is_treated_as_admin(self):
        auth_file = self.secrets_dir / "instructor.json"
        register_instructor(auth_file, "original", "a long original password")
        # Emulate the original project's single-user JSON format.
        saved = json.loads(auth_file.read_text(encoding="utf-8"))
        original_user = saved["users"][0]
        auth_file.write_text(json.dumps({"username": original_user["username"], "password_hash": original_user["password_hash"]}), encoding="utf-8")

        self.assertEqual(get_account_role(auth_file, "original"), "admin")
        create_instructor_account(auth_file, "original", "new_teacher", "a long teacher password")
        self.assertEqual(get_account_role(auth_file, "new_teacher"), "instructor")

    def test_encryption_and_wrong_key(self):
        envelope = encrypt_bytes(b"private attendance", self.enc_key, self.mac_key)
        self.assertEqual(decrypt_bytes(envelope, self.enc_key, self.mac_key), b"private attendance")
        with self.assertRaises(ValueError):
            decrypt_bytes(envelope, b"x" * 32, self.mac_key)

    def test_hmac_valid_ciphertext_modified_and_hmac_modified(self):
        envelope = encrypt_bytes(b"attendance", self.enc_key, self.mac_key)
        self.assertTrue(verify_envelope(envelope, self.mac_key))
        changed_cipher = dict(envelope)
        changed_cipher["ciphertext"] = ("0" if envelope["ciphertext"][0] != "0" else "1") + envelope["ciphertext"][1:]
        self.assertFalse(verify_envelope(changed_cipher, self.mac_key))
        changed_hmac = dict(envelope)
        changed_hmac["hmac"] = "0" * 64
        self.assertFalse(verify_envelope(changed_hmac, self.mac_key))

    def test_status_validation(self):
        self.assertEqual(validate_status("Present"), "Present")
        self.assertEqual(validate_status("Absent"), "Absent")
        with self.assertRaises(ValueError):
            validate_status("Late")

    def test_tampering_demo_preserves_original(self):
        data_file = self.root / "data" / "attendance.enc"
        store = AttendanceStore(data_file, self.secrets_dir)
        store.save(sample_records())
        original_bytes = data_file.read_bytes()
        self.assertTrue(store.tampering_demo())
        self.assertEqual(data_file.read_bytes(), original_bytes)
        self.assertTrue(store.verify_file())
        self.assertEqual(len(list(data_file.parent.iterdir())), 1)

    def test_store_file_is_encrypted_json_envelope(self):
        data_file = self.root / "data" / "attendance.enc"
        store = AttendanceStore(data_file, self.secrets_dir)
        records = sample_records()
        store.save(records)
        saved = data_file.read_text(encoding="utf-8")
        self.assertNotIn("Aditi Sharma", saved)
        self.assertEqual(store.load(), records)
        self.assertEqual(set(json.loads(saved)), {"version", "nonce", "ciphertext", "hmac"})


if __name__ == "__main__":
    unittest.main()
