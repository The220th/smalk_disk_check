# coding: utf-8

from ksupk import singleton_decorator
import threading
import queue
import time
import os
import traceback
import requests
from alerk_pack.message import MessageWrapper, KMessage, MessageContainer, MessageEn
from alerk_pack.crypto import AES256Key, RSAPrivateKey, RSAPublicKey, sym_encrypt, bytes2str


@singleton_decorator
class Kommunicator:

    def __init__(self, url: str,
                 priv_key: RSAPrivateKey, public_key: RSAPublicKey,
                 sign_key: RSAPrivateKey, verify_key: RSAPublicKey,
                 alerk_pub_key: RSAPublicKey, alerk_verify_key: RSAPublicKey,
                 sym_key: AES256Key):

        self.url = url

        self.priv_key: RSAPrivateKey = priv_key
        self.public_key: RSAPublicKey = public_key
        self.sign_key: RSAPrivateKey = sign_key
        self.verify_key: RSAPublicKey = verify_key
        self.alerk_pub_key: RSAPublicKey = alerk_pub_key
        self.alerk_verify_key: RSAPublicKey = alerk_verify_key
        self.sym_key: AES256Key = sym_key

        self.task_queue = queue.Queue()
        self.running = False
        self.thread = threading.Thread(target=self.__run_wrap)
        self.__lock: threading.Lock = threading.Lock()

    def start(self):
        if self.running:
            raise RuntimeError("Already running. ")
        self.thread.start()
        self.running = True

    def __run_wrap(self):
        while True:
            try:
                self.__run()
            except Exception as e:
                error_text = f"{traceback.format_exc()}\n{e}"
                print(error_text)

    def __run(self):
        while True:
            msg_tuple = self.task_queue.get()
            try:
                    msg_wrapper: MessageWrapper = msg_tuple[0]
                    raws: list[tuple[str, bytes]] | None = msg_tuple[1]
                    self.__send_message(msg_wrapper, raws)
            except Exception as e:
                error_text = f"{traceback.format_exc()}\n{e}"
                print(error_text)
                self.add_msg(msg_tuple[0], msg_tuple[1])
                time.sleep(30)
            finally:
                self.task_queue.task_done()

    def __encrypt_raws(self, raws: list[tuple[str, bytes]], sym_key: AES256Key):
        raws_en = []
        txt_formats = [".txt", ".md", ".toml", ".csv", ".json", ".xml", ".yaml", ".html", ".log"]
        for raw_i in raws:
            name = raw_i[0]
            content = sym_encrypt(raw_i[1], sym_key)
            if name.strip() != "" and os.path.splitext(name)[1].lower() in txt_formats:
                content = bytes2str(content).encode(encoding="utf-8")
            raws_en.append((name, content))
        return raws_en

    def __send_message(self, mw: MessageWrapper, raws: list[tuple[str, bytes]] | None):
        priv_key = self.priv_key
        public_key = self.public_key

        sign_key = self.sign_key
        verify_key = self.verify_key

        alerk_pub_key = self.alerk_pub_key
        alerk_verify_key = self.alerk_verify_key

        message_wrapper = mw
        url = self.url

        sym_key = self.sym_key
        if sym_key is not None and raws is not None:
            raws = self.__encrypt_raws(raws, sym_key)
        if raws is None:
            raws = []

        kmsg = KMessage(text=message_wrapper.to_json(), raws=raws)
        kimg_as_data = kmsg.to_dict(sign_key, verify_key)

        message_container = MessageContainer(kimg_as_data)
        encrypted_message_container = message_container.encrypt(alerk_pub_key)

        men: MessageEn = encrypted_message_container.get_data()
        men_d = men.to_dict()

        response = requests.post(url, json=men_d)
        if response.status_code != 200:
            raise RuntimeError(f"(Kommunicator.__send_message) response.status_code != 200: {response}, {response.content}")

        men_d = response.json()
        men = MessageEn.from_dict(men_d)
        encrypted_message_container = MessageContainer(men)
        message_container = encrypted_message_container.decrypt(priv_key)

        kimg_as_data = message_container.get_data()

        kmsg = KMessage.from_dict(kimg_as_data, alerk_verify_key)

        raws = kmsg.get_raws()
        json_text = kmsg.get_text()

        message_wrapper = MessageWrapper.from_json(json_text)

        if message_wrapper.get_type() == MessageWrapper.MSG_TYPE_OK:
            return
        elif message_wrapper.get_type() == MessageWrapper.MSG_TYPE_ERROR:
            raise RuntimeError(f"(Kommunicator.__send_message) Error status code={message_wrapper.get_type()} in answer from alerk. "
                               f"Message text: \"{message_wrapper.get_text()}\". ")

    def add_msg(self, mw: MessageWrapper, raws: list[tuple[str, bytes]] | None = None):
        """
        Add message to queue.Queue to send by Kommunicator. Do not forget to call Kommunicator.start to turn on Kommunicator.

        :param mw: text
        :param raws: attachments, which will be encrypted, if sym_key: AES256Key in Kommunicator.__init__ defined.
        :return:
        """
        with self.__lock:
            self.task_queue.put((mw, raws))
