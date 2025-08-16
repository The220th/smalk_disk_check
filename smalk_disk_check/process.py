# coding: utf-8

import time
import traceback
import datetime
from alerk_pack.message import MessageWrapper
from alerk_pack.communicator import Kommunicator

from smalk_disk_check.setting_manager import SettingManager
from smalk_disk_check.disk import DiskManager, Disk


def check_first_time():
    sm = SettingManager()
    prefix_message = sm.get_prefix_message()

    if sm.notify_if_turned_on():
        startup_message = sm.get_startup_message()
        mw = MessageWrapper(msg_type=MessageWrapper.MSG_TYPE_REPORT, text=f"{prefix_message} {startup_message}", is_attachments=False)
        kommunicator = Kommunicator()
        kommunicator.add_msg(mw)


def main_loop():
    while True:
        try:
            sm = SettingManager()
            kommunicator = Kommunicator()
            disk_manager = DiskManager()
            disks: list[Disk] = disk_manager.get_disks()
            last_disk_check_time, last_full_report_time = None, None
            disk_polling_rate, full_report_period = sm.disk_polling_rate(), sm.full_report_period()
            prefix_message = sm.get_prefix_message()
            problem_message = sm.get_problem_message()
            full_report_message = sm.get_full_report_message()

            test_start(disks)

            check_first_time()

            while True:
                time.sleep(30)
                cur_time = time.time()
                if last_disk_check_time is None or cur_time - last_disk_check_time >= disk_polling_rate:
                    problems, text, problem_disks = disk_polls(disks)
                    if problems:
                        mw = MessageWrapper(msg_type=MessageWrapper.MSG_TYPE_REPORT, text=f"{prefix_message} {problem_message}: {problem_disks}. ",
                                            is_attachments=True)
                        raws = [("re.txt", text.encode(encoding="utf-8"))]
                        kommunicator.add_msg(mw, raws=raws)
                    last_disk_check_time = time.time()
                if last_full_report_time is None or cur_time - last_full_report_time >= full_report_period:
                    full_report = full_disk_report(disks)
                    mw = MessageWrapper(msg_type=MessageWrapper.MSG_TYPE_REPORT, text=f"{prefix_message} {full_report_message}. ",
                                            is_attachments=True)
                    raws = [("r.txt", full_report.encode(encoding="utf-8"))]
                    kommunicator.add_msg(mw, raws=raws)
                    last_full_report_time = time.time()
        except Exception as e:
            print(f"Something gone wrong: {e}. Restarting...")
            error_text = f"{traceback.format_exc()}\n{e}"
            print(error_text)
            time.sleep(5)


def get_cur_time():
    template = "%Y.%m.%d %H:%M:%S"
    time_str = datetime.datetime.now().strftime(template)
    return time_str


def test_start(disks: list[Disk]):
    try:
        if_problem, problem_text, problem_disk_code_list = disk_polls(disks)
        if if_problem:
            print("Cannot test check disks. Is all settings correct? ")
            print(f"Problems disks: {problem_disk_code_list}, text: \n{problem_text}")
            if SettingManager().get_interactive():
                user_input_orig = input("Press Enter to exit or type \"continue\" to continue: ")
                user_input = user_input_orig.strip().lower()
                if user_input == "":
                    exit(1)
                elif user_input == "continue":
                    return
                else:
                    print(f"Cannot understand \"{user_input_orig}\". Exit.")
                    exit(1)
            else:
                return

        full_disk_report(disks)
    except Exception as e:
        error_text = f"{traceback.format_exc()}\n{e}"
        print(error_text)
        print("Cannot test check disks. Is all settings correct? ")
        exit(1)


def disk_polls(disks: list[Disk]) -> tuple[bool, str, list[str]]:
    """

    :param disks:
    :return: if_problem, problem_text, problem_disk_code_list
    """
    cur_time = get_cur_time()
    delimiter = "="*80
    if_problem, problem_text, problem_disk_code_list = False, "", []
    for disk_i in disks:
        try:
            check_success, text = disk_i.check()
            if not check_success:
                problem_text += f"{delimiter}\nDisk \"{disk_i.get_name()}\" ({disk_i.get_dev_path()}) has problem: \n{text}\n\n\n"
                if_problem = True
                problem_disk_code_list.append(disk_i.get_code())
        except Exception as e:
            error_text = f"{traceback.format_exc()}\n{e}"
            problem_text += f"{delimiter}\nDisk \"{disk_i.get_name()}\" ({disk_i.get_dev_path()}) error while checking: \n{error_text}\n\n\n"
            if_problem = True
            problem_disk_code_list.append(disk_i.get_code())
    if if_problem:
        problem_text = f"{cur_time}: \n\n\n" + problem_text
    return if_problem, problem_text, problem_disk_code_list,


def full_disk_report(disks: list[Disk]) -> str:
    cur_time = get_cur_time()
    res = f"{cur_time}: \n\n\n"
    delimiter = "="*80
    for disk_i in disks:
        try:
            disk_i_report_text = disk_i.get_report()
            res += f"{delimiter}\nDisk \"{disk_i.get_name()}\" ({disk_i.get_dev_path()}): \n\n\n{disk_i_report_text}"
        except Exception as e:
            error_text = f"{traceback.format_exc()}\n{e}"
            res += f"{delimiter}\nDisk \"{disk_i.get_name()}\" ({disk_i.get_dev_path()}) error while checking: \n{error_text}\n\n\n"

    return res
