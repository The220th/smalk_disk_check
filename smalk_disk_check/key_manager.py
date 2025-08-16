# coding: utf-8

from ksupk import singleton_decorator
from alerk_pack.crypto import str_to_asym_key, str_to_sym_key, AES256Key, RSAPrivateKey, RSAPublicKey

from smalk_disk_check.setting_manager import SettingManager


@singleton_decorator
class KeyManager:

    def __init__(self, sm: SettingManager):
        self.priv_key, self.pub_key, self.sign_key, self.verify_key = sm.get_my_keys()
        self.alerk_pub_key, self.alerk_verify_key = sm.get_alerk_keys()
        self.sym_key_str = sm.get_sym_key()

        self.priv_key: RSAPrivateKey = str_to_asym_key(self.priv_key, False)
        self.pub_key: RSAPublicKey = str_to_asym_key(self.pub_key, True)
        self.sign_key: RSAPrivateKey = str_to_asym_key(self.sign_key, False)
        self.verify_key: RSAPublicKey = str_to_asym_key(self.verify_key, True)

        self.alerk_pub_key: RSAPublicKey = str_to_asym_key(self.alerk_pub_key, True)
        self.alerk_verify_key: RSAPublicKey = str_to_asym_key(self.alerk_verify_key, True)

        self.sym_key: AES256Key | None = None
        if self.sym_key_str.strip() == "":
            self.sym_key = None
        else:
            self.sym_key = str_to_sym_key(self.sym_key_str)

    def get_priv_key(self) -> RSAPrivateKey:
        return self.priv_key

    def get_pub_key(self) -> RSAPublicKey:
        return self.pub_key

    def get_sign_key(self) -> RSAPrivateKey:
        return self.sign_key

    def get_verify_key(self) -> RSAPublicKey:
        return self.verify_key

    def get_alerk_pub_key(self) -> RSAPublicKey:
        return self.alerk_pub_key

    def get_alerk_verify_key(self) -> RSAPublicKey:
        return self.alerk_verify_key

    def get_sym_key(self) -> AES256Key | None:
        return self.sym_key
