import os.path
import re
import shlex

# unpublished
__version__ = '0.2.0'

# Static metadata

codename = 'KINGDOM'
title = f'Hijack ({codename}) S01'
title_id = "A0059301_ORG"
facility = "Cinelab Film and Digital, 715 Banbury Avenue, Slough, SL1 7LR, UK"


class A001Block:

    def __init__(self, input_mhl_file_name):

        self.mhl_file_name = input_mhl_file_name

        # setup variables
        self.shoot_day_dates = None
        self.sound_rolls = None
        self.cam_rolls = None

        # static elements
        self.codename = codename
        self.title = title
        self.title_id = title_id
        self.facility = facility
        self.mhl_date = ""

        self.files = []
        self.sizes = []
        self.md5s = []
        self.tool = ""

        self.read_mhl_file()

        self.get_unique_elements()
        self.metadata = self.generate_dictionary()
        self.print_summary()
        self.save_to_file()

    def read_mhl_file(self):

        print("\nReading MHL file... This may take a while for frame-based formats")

        with open(self.mhl_file_name, 'r') as mhl_file:

            lines = mhl_file.readlines()

            for index, line in enumerate(lines):

                if (index / 5) == int(index / 5):
                    print_progress_bar(index, len(lines))

                if line.strip().startswith("<file>"):
                    self.files.append(strip_xml_tags(line))

                elif line.strip().startswith("<size>"):
                    self.sizes.append(strip_xml_tags(line))

                elif line.strip().startswith("<md5>"):
                    self.md5s.append(strip_xml_tags(line))

                elif line.strip().startswith("<finishdate>"):

                    self.mhl_date = strip_xml_tags(line)

                elif line.strip().startswith("<tool>"):

                    self.tool = strip_xml_tags(line)

            print_progress_bar(len(lines), len(lines))
            print("\n")

        if len(self.files) != len(self.sizes) or len(self.files) != len(self.md5s):
            raise Exception("Files, sizes and md5s are not equal in length")

        if self.mhl_date == "":
            print("{}No date found in mhl file{}".format(PrintColors.WARNING, PrintColors.ENDC))

        if self.tool == "":
            print("{}No write software version found in mhl file{}".format(PrintColors.WARNING, PrintColors.ENDC))

    # noinspection PyDictCreation
    def generate_dictionary(self):

        metadata = {}

        metadata["TITLE"] = self.title
        metadata["TITLE ID"] = self.title_id
        metadata["FACILITY BARCODE"] = self.facility_barcode(add_version=True)
        metadata["FACILITY"] = self.facility
        metadata["DATE WRITTEN"] = self.date_written
        metadata["MEDIUM"] = "LTO-7"
        metadata["WRITE FORMAT"] = 'LTFS 2.4.0'
        metadata["WRITE VERSION"] = 'MacOS 10.15.7 {}'.format(self.tool)
        metadata["TOTAL FILES"] = str(len(self.files) + 4)
        metadata["TOTAL SIZE"] = total_files_size(self.sizes)
        metadata["CONTENT"] = "Digital Picture Source / Dailies"
        metadata["DELIVERABLE ID"] = "A001"
        metadata["SET ID"] = self.set_id
        metadata["TAPE IN SET"] = self.tape_in_set
        metadata["MD5 HASH VALUE"] = self.facility_barcode(add_version=False) + '.md5'
        metadata["FILE FORMAT"] = ', '.join(self.file_formats())
        metadata["CAMERA TYPES"] = ', '.join(self.camera_types())
        metadata["SHOOT DATE"] = ', '.join(self.shoot_dates())
        metadata["SHOOT DAY NUMBER"] = ', '.join(self.shoot_day_numbers())
        metadata["CAMERA ROLL NUMBERS / SOUND ROLL NUMBERS"] = ', '.join(self.cam_rolls + self.sound_rolls)
        metadata["UNIT REFERENCE"] = ', '.join(self.unit_references())
        metadata["PROCESS METADATA"] = 'N/A'
        metadata["CAMERA FILE EXTRACTION"] = ', '.join(self.camera_file_extraction())
        metadata["NOTES"] = f"{self.facility_barcode()}.txt (in main directory of LTO) for list of all files. Copy " \
                            f"of this txt file has been emailed to Apple Archive. "
        metadata["FILES"] = f"{self.facility_barcode()}.txt"

        return metadata

    def facility_barcode(self, add_version=False):

        barcode = os.path.basename(self.mhl_file_name)

        if add_version:
            return barcode.replace('.mhl', 'L7')
        else:
            return barcode.replace(".mhl", "")

    @property
    def date_written(self):

        date = self.mhl_date[0:10]
        date = mil_date_to_date(date)
        return '/'.join(date)

    @property
    def set_id(self):

        tape = self.facility_barcode()
        tape_last_digit = int(tape[-1])

        if tape_last_digit % 2 == 1:
            return "A"
        else:
            return "B"

    @property
    def tape_in_set(self):

        tape = self.facility_barcode()
        tape_last_digit = int(tape[-3:])

        if self.set_id == "A":

            tape_set = int((tape_last_digit + 1) / 2)
        else:
            tape_set = int( (tape_last_digit / 2))

        return f'{int(tape_set)} of X'

    def file_formats(self):

        file_formats = [x.split(".")[-1].lower() for x in self.files] + ["mhl", "md5", "txt"]
        file_formats = list(dict.fromkeys(file_formats))
        file_formats.sort()
        return file_formats

    def get_unique_elements(self):

        shoot_day_dates = []
        cam_rolls = []
        sound_rolls = []

        for file in self.files:
            file_path_split = file.split("/")
            shoot_day_dates.append(file_path_split[3])
            if file_path_split[4] == "CAMERA" or file_path_split[4] == "MEZZANINE":
                cam_rolls.append(file_path_split[5])
            elif file_path_split[4] == "SOUND":
                sound_rolls.append(file_path_split[5])
            else:
                raise Exception("Unknown folder type: " + file_path_split[4])

        self.cam_rolls = list(dict.fromkeys(cam_rolls))
        self.sound_rolls = list(dict.fromkeys(sound_rolls))
        self.shoot_day_dates = list(dict.fromkeys(shoot_day_dates))

    def shoot_dates(self):

        print(self.shoot_day_dates[0])
        dates = [x.split('-', 1)[0] for x in self.shoot_day_dates]
        print(dates)
        dates = [x.split('_')[-1] for x in dates]
        print(dates)
        dates = list(dict.fromkeys(dates))

        dates = ['/'.join(mil_date_to_date(x)) for x in dates]

        print(dates)

        return dates

    def shoot_day_numbers(self):

        days = [x.split('-', 1)[-1] for x in self.shoot_day_dates]
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

    def camera_file_extraction(self):

        format_map = {
            "ari": "ARRIRAW",
            "arx": "ARRIRAW (HDE)",
            "r3d": "REDCODE RAW"
        }

        format_types = []

        for file_type in self.file_formats():

            if file_type in format_map:
                format_types.append(format_map[file_type])
            else:
                print("{}Some camera formats could not be mapped to a extraction!{}".format(PrintColors.WARNING,
                                                                                            PrintColors.ENDC))

        return format_types

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
            "mp4": "OTHER"
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

    def print_summary(self):

        print('\n')
        print("{}Metadata Block{}".format(PrintColors.UNDERLINE, PrintColors.ENDC))

        for key, value in self.metadata.items():
            print("{}{}{}: {}".format(PrintColors.OKBLUE, key, PrintColors.ENDC, value))

    def save_to_file(self):

        breaks_after = ["TOTAL SIZE", "CAMERA FILE EXTRACTION", "NOTES", 'FILES']

        filename = os.path.abspath(self.mhl_file_name)
        filename = os.path.dirname(filename)
        filename = os.path.join(filename,
                                f'{self.codename}_A001_{self.facility_barcode(add_version=True)}_METADATA.txt')

        with open(filename, "w") as f:
            for key, value in self.metadata.items():

                f.write("{}: {}\n".format(key, value))

                if key in breaks_after:
                    f.write("\n")


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


def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='#'):
    percent = iteration / total * 100
    bar_count = (int(length * (iteration / total)))
    empty_count = length - bar_count
    bar = (fill * bar_count) + " " * empty_count

    print(f'\r{prefix}|{bar}| {round(percent)}% complete {suffix}', end="", flush=True)


if __name__ == "__main__":

    print("{}Apple Metadata Block Generator{}".format(PrintColors.UNDERLINE, PrintColors.ENDC))
    print("Version: {} {}".format(__version__, title))

    filenames = input("Drop tape MHLs here...")

    filenames = shlex.split(filenames)
    filenames = [filename for filename in filenames if re.search(r'[mM][hH][lL]$', filename)]

    # Check validity of files
    valid_filenames = []
    for filename in filenames:

        if os.path.isfile(filename):
            valid_filenames.append(filename)

    print("\nFound", str(len(valid_filenames)))
    print("\n".join(valid_filenames))

    for filename in valid_filenames:
        A001Block(filename)

    print("\nDone!")
