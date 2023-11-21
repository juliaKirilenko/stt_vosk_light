import sys, os
import argparse
import logging
import logging.handlers
import time
import json
from stt import STTClass

class JSONFormatter(logging.Formatter):

    def __init__(self) -> None:
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        json_dict = {'time': self.formatTime(record), 'levelname': record.__dict__['levelname'], 'message': record.getMessage()}
        return json.dumps(json_dict)

def logging_init(log_dir):
    log_file = 'L' + time.strftime('%Y%m%d', time.gmtime()) + '.log'
    log_file = os.path.join(log_dir, log_file)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(JSONFormatter())

    log_console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_console_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

if __name__ == '__main__':
    # Command line arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--file_config', required=False)
    args = arg_parser.parse_args()

    # Default values
    file_config = os.path.join(os.getcwd(), "conf.JSON")    # by default use conf file in current directory
    configs = []

    # Validate config file
    if args.file_config:
        file_config = args.file_config
    if not os.path.isfile(file_config):
        e = 'Configuration file {} is not valid or not exist. Please change or add configuration file.'.format(file_config)
        sys.exit(e)
    try:
        with open(file_config) as json_file:
            dict_conf = json.load(json_file)
    except ValueError as ve:
        e = 'Data in {} is invalid. Please use standart format.'.format(file_config)
        sys.exit(e)

    mandatory = ['audio_path', 'result_path', 'function']
    conf_keys = dict_conf.keys()
    absents = [absent for absent in mandatory if absent not in conf_keys]
    if absents:
        e = 'Required parameters {} are missing in the configuration file. Please add them.'.format(absents)
        sys.exit(e)

    audio_path = dict_conf['audio_path']
    result_path = dict_conf['result_path']
    function = dict_conf['function']

    # Default values
    speed = None
    volume = None
    model_lang = None
    log_dir = 'logs'

    # Validate parameters
    if not os.path.isfile(audio_path):
        e = 'Audio path {} is not valid. Please change audio path.'.format(audio_path)
        sys.exit(e)
    if os.path.isfile(result_path):
        e = 'Result file {} exists. Please change result file.'.format(result_path)
        sys.exit(e)
        if function == "achange" and result_path.split('.')[-1] != 'wav':
            e = 'Result file {} format is invalid. Please change result file format.'.format(result_path)
            sys.exit(e)
    if function not in ["transcript", "achange"]:
        e = 'Function {} is invalid. Please use function from {}.'.format(function, '(transcript, achange)')
        sys.exit(e)
    if function == "achange":
        if 'speed' in conf_keys:
            try:
                speed = float(dict_conf['speed'])
            except ValueError as ve:
                e = 'Speed {} is invalid. It must be a number.'.format(dict_conf['speed'])
                sys.exit(e)
            if speed <= 0:
                e = 'Speed {} is invalid. It must be a positive number.'.format(dict_conf['speed'])
                sys.exit(e)
        if 'volume' in conf_keys:
            try:
                volume = float(dict_conf['volume'])
            except ValueError as ve:
                e = 'Volume {} is invalid. It must be a number.'.format(dict_conf['volume'])
                sys.exit(e)
            if volume <= 0:
                e = 'Volume {} is invalid. It must be a positive number.'.format(dict_conf['volume'])
                sys.exit(e)
        if not (speed or volume):
            e = 'Neither speed nor volume are specified. Please indicate at least one of these parameters.'
            sys.exit(e)
    if function == "transcript":
        if 'model_lang' in conf_keys:
            model_lang = dict_conf['model_lang']
        if model_lang not in ["ru", "en"]:
            e = 'Model language {} is invalid. Please use language from {}.'.format(model_lang, '(ru, en)')
            sys.exit(e)
    if 'log_dir' in conf_keys:
        log_dir = dict_conf['log_dir']
        if not os.path.isdir(log_dir):
            e = f'Logging folder {log_dir} is not valid. Please change logs folder.'
            sys.exit(e)
    else:
        try:
            os.mkdir(log_dir)
        except FileExistsError:
            pass
    logging_init(log_dir)

    # Create and initialize
    sttSpVol = STTClass(audio_path, result_path, function, speed, volume, model_lang)

    if function == "transcript":
        logging.info('Prepare model...')
        sttSpVol.prepare_model()
        sttSpVol.prepare_tmp()
        logging.info('Done\n')
        sttSpVol.process_transcript()
    elif function == "achange":
        logging.info('Create new audio...')
        sttSpVol.change_audio()
