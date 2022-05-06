import os.path
import re


class A001Block:

    def __init__(self, input_mhl_file_name):

        self.mhl_file_name = input_mhl_file_name

        # setup variables
        self.shoot_day_dates = None
        self.sound_rolls = None
        self.cam_rolls = None

        # static elements
        self.title = "KINGDOM"
        self.title_id = "?"
        self.facility = "Cinelab Film and Digital, 715 Banbury Avenue, Slough, SL1 7LR, UK"
        self.mhl_date = ""

        self.files = []
        self.sizes = []
        self.md5s = []

        self.read_mhl_file()

        self.get_unique_elements()
        self.dictionary = self.generate_dictionary()

    def read_mhl_file(self):

        with open(self.mhl_file_name, 'r') as mhl_file:

            lines = mhl_file.readlines()

            for index, line in enumerate(lines):

                if line.strip().startswith("<file>"):
                    self.files.append(strip_xml_tags(line))

                elif line.strip().startswith("<size>"):
                    self.sizes.append(strip_xml_tags(line))

                elif line.strip().startswith("<md5>"):
                    self.md5s.append(strip_xml_tags(line))

                elif line.strip().startswith("<finishdate>"):

                    self.mhl_date = strip_xml_tags(line)

    # noinspection PyDictCreation
    def generate_dictionary(self):

        dictionary = {}

        dictionary["TITLE"] = self.title
        dictionary["TITLE ID"] = self.title_id
        dictionary["FACILITY BARCODE"] = self.facility_barcode(add_version=True)
        dictionary["FACILITY"] = self.facility
        dictionary["DATE WRITTEN"] = self.date_written()
        dictionary["MEDIUM"] = "LTO-7"
        dictionary["WRITE FORMAT"] = 'LTFS 2.2'
        dictionary["WRITE VERSION"] = 'MacOS Catalina - YoYotta'
        dictionary["TOTAL FILES"] = len(self.files) + 4
        dictionary["TOTAL SIZE"] = total_files_size(self.sizes)
        dictionary["CONTENT"] = "Digital Picture Source / Dailies"
        dictionary["DELIVERABLE ID"] = "A001"
        dictionary["SET ID"] = self.set_id()
        dictionary["TAPE IN SET"] = '1 of 1'
        dictionary["MD5 HASH VALUE"] = "N/A"
        dictionary["FILE FORMAT"] = ', '.join(self.file_formats())
        dictionary["CAMERA TYPES"] = ', '.join(self.camera_types())
        dictionary["SHOOT DATE"] = ', '.join(self.shoot_dates())
        dictionary["SHOOT DAY NUMBER"] = ', '.join(self.shoot_day_numbers())
        dictionary["CAMERA ROLL NUMBERS / SOUND ROLL NUMBERS"] = ', '.join(self.cam_rolls + self.sound_rolls)
        dictionary["UNIT REFERENCE"] = ', '.join(self.unit_references())
        dictionary["PROCESS METADATA"] = 'N/A'
        dictionary["CAMERA FILE EXTRACTION"] = 'N/A'
        dictionary["NOTES"] = f"{self.facility_barcode()}.txt (in main directory of LTO) for list of all files. Copy of this txt file has been emailed to Apple Archive. "
        dictionary["FILES"] = f"{self.facility_barcode()}.txt"

        return dictionary

    def facility_barcode(self, add_version=False):

        barcode = os.path.basename(self.mhl_file_name)

        if add_version:
            return barcode.replace('.mhl', 'L7')
        else:
            return barcode.replace(".mhl", "")

    def date_written(self):

        date = self.mhl_date[0:10]
        date = mil_date_to_date(date)
        return '/'.join(date)

    def set_id(self):

        tape = self.facility_barcode()
        tape_last_digit = int(tape[-1])

        if tape_last_digit % 2 == 1:
            return "A"
        else:
            return "B"

    def file_formats(self):

        file_formats = [x.split(".")[-1] for x in self.files] + ["mhl", "md5", "txt"]
        file_formats = list(dict.fromkeys(file_formats))
        file_formats.sort()
        return file_formats

    def get_unique_elements(self):

        shoot_day_dates = []
        cam_rolls = []
        sound_rolls = []

        for file in self.files:
            file_path_split = file.split("/")

            shoot_day_dates.append(file_path_split[4])
            if file_path_split[5] == "Camera_Media":
                cam_rolls.append(file_path_split[6])
            elif file_path_split[5] == "Sound_Media":
                sound_rolls.append(file_path_split[6])
            else:
                raise Exception("Unknown folder type: " + file_path_split[5])

        self.cam_rolls = list(dict.fromkeys(cam_rolls))
        self.sound_rolls = list(dict.fromkeys(sound_rolls))
        self.shoot_day_dates = list(dict.fromkeys(shoot_day_dates))

    def shoot_dates(self):

        dates = [x[0:8] for x in self.shoot_day_dates]
        dates = list(dict.fromkeys(dates))

        dates = ['/'.join(mil_date_to_date(x)) for x in dates]

        return dates

    def shoot_day_numbers(self):

        days = [x.split('_', 1)[-1] for x in self.shoot_day_dates]
        days = list(dict.fromkeys(days))

        return days

    def unit_references(self):

        unit_map = {
            "MU": "Main Unit",
            "2U": "Second Unit",
            "SU": "Splinter Unit"
        }

        days = self.shoot_day_numbers()

        unit_refs = []

        for day in days:

            for unit in unit_map:
                if unit in day:
                    unit_refs.append(unit_map[unit])

        # Remove duplicates
        unit_refs = list(dict.fromkeys(unit_refs))

        return unit_refs

    def camera_types(self):

        camera_map = {
            "ari": "Alexa",
            "arx": "Alexa",
            "r3d": "Red",
            "crm": "Canon",
            "braw": "Blackmagic",
            "mxf": "OTHER",
            "dng": "OTHER",
            "mov": "OTHER",
            "mp4": "OTHER",
            "wav": "OTHER"
        }

        file_types = self.file_formats()

        camera_types = []

        for file_type in file_types:
            if file_type in camera_map:
                camera_types.append(camera_map[file_type])

        # Remove duplicates
        camera_types = list(dict.fromkeys(camera_types))

        if "OTHER" in camera_types:
            print("{}Some camera formats could not be mapped to a camera type{}".format(PrintColors.WARNING,
                                                                                        PrintColors.ENDC))

        return camera_types


def mil_date_to_date(mil_date):
    if '-' in mil_date:
        date_items = mil_date.split("-")
    elif '/' in mil_date:
        date_items = mil_date.split("/")
    else:
        date_items = [mil_date[0:4], mil_date[4:6], mil_date[6:8]]

    date_items.reverse()

    return date_items


def strip_xml_tags(string):
    string = string.strip()
    string = re.sub(r'<.*?>', '', string)

    return string


def total_files_size(sizes):
    total_size = sum([int(x) for x in sizes])

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if total_size < 1000:
            return str(round(total_size, 2)) + unit
        total_size /= 1000


class PrintColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█'):
    bar = fill * int(length * iteration // total)
    suffix = ' ' + suffix

    print('\r{} [{}]  {}'.format(prefix, bar, suffix), end="")


if __name__ == "__main__":
    block = A001Block("sample_data/MQ0292.mhl")

    for key, value in block.dictionary.items():
        print(f'{PrintColors.OKGREEN}{key}{PrintColors.ENDC}: {value}')
