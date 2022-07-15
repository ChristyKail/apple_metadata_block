import os.path
import re


class AppleMetadataBlockConfig:

    def __init__(self, project):

        self.project = project
        self.load_preset_from_file()

        self.day_level = 3
        self.type_level = 4
        self.roll_level = 5

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

        self.config = AppleMetadataBlockConfig()

        self.mhl_file_path = mhl_file_path
        self.files_dictionary = {}

        self.day_elements = []
        self.camroll_elements = []
        self.soundroll_elements = []

        self.load_mhl_file()

        self.get_unique_elements()

        self.load_config()

        self.facility_barcode = self.get_barcode()

        print('Days: ' + str(self.day_elements))
        print('Camrolls: ' + str(self.camroll_elements))
        print('Soundrolls: ' + str(self.soundroll_elements))

        print('Total size: ' + calculate_size_total(self.files_dictionary.values()))

    def load_mhl_file(self):
        with open(self.mhl_file_path, 'r') as file_handler:

            lines = file_handler.readlines()

            if lines[1].strip() != '<hashlist version="1.1">':
                raise Exception('Invalid MHL file')

            for line in lines:

                line = line.strip()

                if line.startswith('<file>'):

                    path = line.split('<file>')[1].split('</file>')[0]

                    self.files_dictionary[path] = {}

                elif line.startswith('<size>'):

                    size = line.split('<size>')[1].split('</size>')[0]

                    self.files_dictionary[path] = size

    def get_unique_elements(self):

        for index, path in enumerate(self.files_dictionary.keys()):

            path_split = path.split('/')

            if path_split[self.config.day_level] not in self.day_elements:
                self.day_elements.append(path_split[self.config.day_level])

            if path_split[self.config.roll_level] not in (self.camroll_elements + self.soundroll_elements):

                if path_split[self.config.type_level] == "CAMERA":
                    self.camroll_elements.append(path_split[self.config.roll_level])
                elif path_split[self.config.type_level] == "SOUND":
                    self.soundroll_elements.append(path_split[self.config.roll_level])

    def load_config(self):

        project = self.day_elements[0].split('_')[1]
        print("Project", project)

        AppleMetadataBlock(project)

    def get_barcode(self):

        barcode = os.path.basename(self.mhl_file_path).split('.')[0]

        if re.match(r'\w{4}\d{2}$', barcode):
            return barcode

        else:
            raise Exception(f'Invalid barcode {barcode}')


if __name__ == "__main__":
    AppleMetadataBlock("sample_data/KD0097.mhl")
