import os.path
import re


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

    def load_mhl_file(self):

        print(f'Loading {self.mhl_file_path}')

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

        project = self.day_elements[0].split('_')[1]
        print("Project", project)

        return AppleMetadataBlockConfig(project)

    def get_barcode(self):

        barcode = os.path.basename(self.mhl_file_path).split('.')[0]

        if re.match(r'\w{4}\d{2}$', barcode):
            return barcode

        else:
            raise Exception(f'Invalid barcode {barcode}')

    def set_id(self):

        tape_last_digit = int(self.facility_barcode[-1])

        print(f'Tape last digit: {tape_last_digit}')

        if tape_last_digit % 2 == 1:
            return "A"
        else:
            return "B"

    def get_days_dates_units(self):

        days = []
        dates = []
        units = []

        for entry in self.day_elements:

            day_date = entry.split('_')[-1]

            date = mil_date_to_us_date(day_date.split('-')[0])
            day = day_date.split('-')[1]
            unit = day[0:2]

            if day not in days:
                days.append(day)

            if date not in dates:
                dates.append(date)

            if unit not in units:
                units.append(unit)

        for x in units:
            if x == 'MU':
                units.remove(x)
                units.append('Main Unit')

            if x == '2U':
                units.remove(x)
                units.append('Second Unit')

            if x == 'SU':
                units.remove(x)
                units.append('Splinter Unit')

        print(days, dates, units)

        return days, dates, units

    def tape_in_set(self):

        tape = self.facility_barcode
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

        print(formats_dict)

        for camera in self.camroll_elements:
            for format_regex in formats_dict.keys():
                if re.match(format_regex, camera):
                    self.camera_types.append(formats_dict[format_regex][0])
                    self.camera_formats.append(formats_dict[format_regex][1])

#       remove duplicates
        self.camera_types = list(set(self.camera_types))
        self.camera_formats = list(set(self.camera_formats))

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

        print("----------------------------------------------------")
        print(block)

        return block

def mil_date_to_us_date(date):
    if "-" in date:
        year, month, day = date.split("-")
    else:
        year = date[0:4]
        month = date[4:6]
        day = date[6:8]

    return f"{month}/{day}/{year}"


if __name__ == "__main__":
    AppleMetadataBlock("sample_data/KD0097.mhl")
