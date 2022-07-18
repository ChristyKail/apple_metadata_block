import os.path
import re

__version__ = "2.0.0"

import shlex


class AppleMetadataBlockConfig:

    def __init__(self, project):
        self.project = project

        self.template = ""
        self.format_map = ""

        self.load_preset_from_file()

    def load_preset_from_file(self):
        if not os.path.isfile(f'presets/{self.project}.txt'):
            raise Exception(f'Preset file {self.project}.txt does not exist')

        with open(f'presets/{self.project}.txt', 'r') as file_handler:
            file_content = file_handler.read()

            template, format_map = file_content.split("<FORMAT MAPPING>")

            self.template = template.strip()
            self.format_map = format_map.strip()


def calculate_size_total(sizes):
    total_size = sum([int(x) for x in sizes])

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if total_size < 1000:
            return str(round(total_size, 2)) + unit
        total_size /= 1000


class AppleMetadataBlock:

    def __init__(self, mhl_file_path):

        self.mhl_file_path = mhl_file_path
        self.files_dictionary = {}
        self.software = ""
        self.project = ""

        self.day_elements = []
        self.camroll_elements = []
        self.soundroll_elements = []
        self.file_formats = ["mhl", "txt", "md5"]

        self.camera_types = []
        self.camera_formats = []

        self.date_written = ""

        self.day_level = 3
        self.type_level = 4
        self.roll_level = 5

        self.manual_fix = False

        self.load_mhl_file()

        self.get_unique_elements()

        self.config = self.load_config()

        self.facility_barcode = self.get_barcode()

        self.days, self.dates, self.units = self.get_days_dates_units()

        self.map_formats()

        print('Days: ' + str(self.day_elements))
        print('Camrolls: ' + str(self.camroll_elements))
        print('Soundrolls: ' + str(self.soundroll_elements))

        print('Total size: ' + calculate_size_total(self.files_dictionary.values()))

        self.compile_block()
        self.write_block()

    def load_mhl_file(self):

        with open(self.mhl_file_path, 'r') as file_handler:

            lines = file_handler.readlines()

            if lines[1].strip() != '<hashlist version="1.1">':
                raise Exception('Invalid MHL file')

            for line in lines:

                line = line.strip()

                if line.startswith('<startdate>'):
                    self.date_written = mil_date_to_us_date(line.split('>')[1].split('T')[0])

                if line.startswith('<file>'):

                    path = line.split('<file>')[1].split('</file>')[0]

                    self.files_dictionary[path] = {}

                elif line.startswith('<size>'):

                    size = line.split('<size>')[1].split('</size>')[0]

                    self.files_dictionary[path] = size

                elif line.startswith('<tool>'):

                    self.software = line.split('<tool>')[1].split('</tool>')[0]

    def get_unique_elements(self):

        for index, path in enumerate(self.files_dictionary.keys()):

            path_split = path.split('/')

            if path_split[-1].split('.')[-1].lower() not in self.file_formats:
                self.file_formats.append(path_split[-1].split('.')[-1].lower())

            if path_split[self.day_level] not in self.day_elements:
                self.day_elements.append(path_split[self.day_level])

            if path_split[self.roll_level] not in (self.camroll_elements + self.soundroll_elements):

                if path_split[self.type_level] == "CAMERA":
                    self.camroll_elements.append(path_split[self.roll_level])
                elif path_split[self.type_level] == "SOUND":
                    self.soundroll_elements.append(path_split[self.roll_level])

        self.day_elements.sort()
        self.camroll_elements.sort()
        self.soundroll_elements.sort()
        self.file_formats.sort()

    def load_config(self):

        self.project = self.day_elements[0].split('_')[1]

        return AppleMetadataBlockConfig(self.project)

    def get_barcode(self):

        barcode = os.path.basename(self.mhl_file_path).split('.')[0]

        if re.match(r'\w{4}\d{2}$', barcode):
            return barcode

        else:
            raise Exception(f'Invalid barcode {barcode}')

    def set_id(self):

        tape_last_digit = int(self.facility_barcode[-1])

        if tape_last_digit % 2 == 1:
            return "A"
        else:
            return "B"

    def get_days_dates_units(self):

        days = []
        dates = []
        units = []
        unit_names = []

        try:

            for entry in self.day_elements:

                day_date = entry.split('_')[-1]

                date = mil_date_to_us_date(re.findall(r'\d{8}', entry)[0])
                if date not in dates:
                    dates.append(date)

                day = day_date.split('-')[1]
                if day not in days:
                    days.append(day)

                unit = day[0:2]
                if unit not in units:
                    units.append(unit)

        except IndexError:
            print('Non-standard day')
            self.manual_fix = True

        for x in units:
            if x == 'MU':
                unit_names.append('Main Unit')

            elif x == '2U':
                unit_names.append('Second Unit')

            elif x == 'SU':
                unit_names.append('Splinter Unit')

            elif x == 'TE':
                unit_names.append('Tests')

            else:
                print('Unknown unit: ' + x)
                self.manual_fix = True

        print(days, dates, units)

        return days, dates, unit_names

    def tape_in_set(self):

        tape_last_digit = int(self.facility_barcode[-1])

        if self.set_id() == "A":

            tape_set = int((tape_last_digit + 1) / 2)
        else:
            tape_set = int((tape_last_digit / 2))

        return f'{int(tape_set)}'

    def map_formats(self):

        formats_dict = {}

        for line in self.config.format_map.split('\n'):
            line_split = line.split(',')

            formats_dict[line_split[0]] = [line_split[1], line_split[2]]

        for camera in self.camroll_elements:
            camera_detected = False
            for format_regex in formats_dict.keys():
                if re.match(format_regex, camera):
                    self.camera_types.append(formats_dict[format_regex][0])
                    self.camera_formats.append(formats_dict[format_regex][1])
                    camera_detected = True
            if not camera_detected:
                print(f'Camera format not detected: {camera}')
                self.manual_fix = True

        # remove duplicates
        self.camera_types = list(set(self.camera_types))
        self.camera_formats = list(set(self.camera_formats))

        self.camera_types.sort()
        self.camera_formats.sort()

    def compile_block(self):

        block = self.config.template

        block = block.replace('{SOFTWARE}', self.software)
        block = block.replace('{BARCODE}', self.facility_barcode)

        block = block.replace('{SETID}', self.set_id())

        block = block.replace('{TAPEINSET}', self.tape_in_set())

        block = block.replace('{DATE}', self.date_written)
        block = block.replace('{TOTALFILES}', str(len(self.files_dictionary)))
        block = block.replace('{TOTALSIZE}', calculate_size_total(self.files_dictionary.values()))

        block = block.replace('{CAMERASOUNDROLLNUMBERS}', ', '.join(self.camroll_elements + self.soundroll_elements))
        block = block.replace('{FILEFORMAT}', ', '.join(self.file_formats))
        block = block.replace('{SHOOTDAYNUMBER}', ', '.join(self.days))
        block = block.replace('{SHOOTDATE}', ', '.join(self.dates))
        block = block.replace('{UNITREFERENCE}', ', '.join(self.units))

        block = block.replace('{CAMERATYPES}', ', '.join(self.camera_types))
        block = block.replace('{CAMERAFILEEXTRACTION}', ', '.join(self.camera_formats))

        block = block.replace('{CAMERASOUND}', ', '.join(self.camroll_elements))

        return block

    def write_block(self):

        block = self.compile_block()

        if self.manual_fix:
            manual_fix = " - Manual Fix"
        else:
            manual_fix = ""

        output_filename = f'{self.project}_A001_{self.facility_barcode}L7_METADATA{manual_fix}.txt'

        output_file = os.path.dirname(self.mhl_file_path) + '/' + output_filename

        with open(output_file, 'w') as f:
            f.write(block)


def mil_date_to_us_date(date):

    if "-" in date:
        year, month, day = date.split("-")
    else:
        year = date[0:4]
        month = date[4:6]
        day = date[6:8]

    return f"{month}/{day}/{year}"


if __name__ == "__main__":
    print(f"Apple Metadata Block Generator {__version__}")
    filenames = input("Drop tape MHLs here...")
    filenames = shlex.split(filenames)

    for filename in filenames:

        if os.path.isfile(filename) and filename.endswith('.mhl'):
            print(f"Processing {os.path.basename(filename)}")
            AppleMetadataBlock(filename)

        elif os.path.isdir(filename):
            print(f"Processing folder {os.path.basename(filename)}")
            for filename_in_folder in os.listdir(filename):
                if filename_in_folder.endswith('.mhl'):
                    print(f"Processing {os.path.basename(filename_in_folder)}")
                    AppleMetadataBlock(filename + '/' + filename_in_folder)
