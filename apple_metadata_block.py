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

        self.day_elements = []
        self.camroll_elements = []
        self.soundroll_elements = []

        self.date_written = ""

        self.day_level = 3
        self.type_level = 4
        self.roll_level = 5

        self.load_mhl_file()

        self.get_unique_elements()

        self.config = self.load_config()

        self.facility_barcode = self.get_barcode()

        self.days, self.dates, self.units = self.get_days_dates_units()

        print('Days: ' + str(self.day_elements))
        print('Camrolls: ' + str(self.camroll_elements))
        print('Soundrolls: ' + str(self.soundroll_elements))

        print('Total size: ' + calculate_size_total(self.files_dictionary.values()))

    def load_mhl_file(self):

        print(f'Loading {self.mhl_file_path}')

        with open(self.mhl_file_path, 'r') as file_handler:

            lines = file_handler.readlines()

            if lines[1].strip() != '<hashlist version="1.1">':
                raise Exception('Invalid MHL file')

            for line in lines:

                line = line.strip()

                if line.startswith('<startdate>'):
                    self.date_written = line.split('>')[1].split('T')[0]
                    print(f'Date written: {mil_date_to_us_date(self.date_written)}')

                if line.startswith('<file>'):

                    path = line.split('<file>')[1].split('</file>')[0]

                    self.files_dictionary[path] = {}

                elif line.startswith('<size>'):

                    size = line.split('<size>')[1].split('</size>')[0]

                    self.files_dictionary[path] = size

    def get_unique_elements(self):

        for index, path in enumerate(self.files_dictionary.keys()):

            path_split = path.split('/')

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

    def get_days_dates_units(self):

        days = []
        dates = []
        units = []

        for entry in self.day_elements:

            day_date = entry.split('_')[-1]

            date = day_date.split('-')[0]
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

    def compile_block(self):

        block = self.config.template

        block = block.replace('{BARCODE}', self.facility_barcode)
        block = block.replace('{DATE}', self.date_written)

        return block


def mil_date_to_us_date(date):

    year, month, day = date.split("-")

    return f"{month}/{day}/{year}"


if __name__ == "__main__":
    AppleMetadataBlock("sample_data/KD0097.mhl")
