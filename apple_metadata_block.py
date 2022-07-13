class AppleMetadataBlockConfig:

    def __int__(self, day_level=4, type_level=5, roll_level=6):
        self.day_level = day_level
        self.type_level = type_level
        self.roll_level = roll_level


def calculate_size_total(sizes):
    total_size = sum([int(x) for x in sizes])

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if total_size < 1000:
            return str(round(total_size, 2)) + unit
        total_size /= 1000


class AppleMetadataBlock:

    def __init__(self, mhl_file_path):

        self.config = AppleMetadataBlockConfig()

        print(self.config)

        self.mhl_file_path = mhl_file_path
        self.files_dictionary = {}

        self.day_elements = []
        self.roll_elements = []

        self.load_mhl_file()

        self.get_unique_elements()

        print('Days: ' + str(self.day_elements))
        print('Rolls: ' + str(self.roll_elements))

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

        for path in self.files_dictionary.keys():

            path_split = path.split('/')

            if path_split[self.config.day_level] not in self.day_elements:
                self.day_elements.append(path_split[self.config.day_level])

            if path_split(self.config.roll_level) not in self.roll_elements:
                self.roll_elements.append(path_split[self.config.roll_level])


if __name__ == "__main__":
    AppleMetadataBlock("sample_data/KD0097.mhl")
