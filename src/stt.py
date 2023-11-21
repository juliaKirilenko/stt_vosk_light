import sys, os
import tempfile
import logging
import shutil
import json
import time
import re
import ffmpeg
import wave
from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(-1)

class STTClass:

    def __init__(self, audio_path, result_path, function, speed, volume, model_lang):
        self.audio_path = audio_path
        self.result_path = result_path
        self.function = function
        self.speed = speed
        self.volume = volume
        self.model_lang = model_lang

    def prepare_model(self):
        if self.model_lang == 'en':
            model_folder = 'model_en'
        else:
            model_folder = 'model_ru'

        if hasattr(sys, '_MEIPASS') and os.path.isdir(os.path.join(sys._MEIPASS, model_folder)):
            model_folder = os.path.join(sys._MEIPASS, model_folder)
        else:
            s = 'ERROR while loading model'
            logging.error(s)
            sys.exit(s)

        self.model = Model(model_folder)
        shutil.rmtree(model_folder, ignore_errors=True)

    def clean(self):
        if os.path.isdir(self.tmp_folder):
            shutil.rmtree(self.tmp_folder, ignore_errors=True)

    def prepare_tmp(self):
        self.tmp_folder = os.path.join(tempfile.gettempdir(), "stt")
        self.clean()
        try:
            os.mkdir(self.tmp_folder)
        except FileExistsError:
            pass

    def change_audio(self):
        path_to_new_wav = self.audio_path[:-4]
        try:
            stream = ffmpeg.input(self.audio_path)
            if self.speed:
                stream = ffmpeg.filter_(stream, 'atempo', str(self.speed))
                #path_to_new_wav = f'{path_to_new_wav}_speed_{str(self.speed)}'
            if self.volume:
                stream = ffmpeg.filter_(stream, 'volume', str(self.volume))
                #path_to_new_wav = f'{path_to_new_wav}_volume_{str(self.volume)}'
            if self.result_path:
                stream = ffmpeg.output(stream, self.result_path)
            else:
                stream = ffmpeg.output(stream, path_to_new_wav + '.wav')
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            logging.info('Done\n')
        except Exception as e:
            s = f'ERROR while preparing audio: {e}'
            logging.error(s)
            return

    def get_transcription(self, audio_file_path):
        model_full_translation = []

        with wave.open(audio_file_path, 'rb') as wave_data:
            rec = KaldiRecognizer(self.model, wave_data.getframerate())
            while True:
                part_data = wave_data.readframes(4000)
                if len(part_data) == 0:
                    break
                if rec.AcceptWaveform(part_data):
                    result_text = json.loads(rec.Result())
                    if 'text' in result_text:
                        result_text = result_text['text']
                        model_full_translation.append(result_text)
                else:
                    partial = rec.PartialResult()

            result_text = json.loads(rec.FinalResult())
            if 'text' in result_text:
                model_full_translation.append(result_text['text'])

        return model_full_translation

    def write_translation(self, file_name, translation_text):
        #result_txt = os.path.join(self.results_folder, file_name[:-4] + "_traslation.txt")

        json_dict = {'filename': file_name, 'text': " ".join(translation_text)}
        with open(self.result_path, 'w', encoding='utf-8') as out:
            json.dump(json_dict, out, indent = 4, ensure_ascii=False)

    def process_transcript(self):
        audio_file_name = os.path.split(self.audio_path)[-1]

        start_time = time.time()
        tmp_audio_path = os.path.join(self.tmp_folder, audio_file_name)
        try:
            stream = ffmpeg.input(self.audio_path)
            stream = ffmpeg.output(stream, tmp_audio_path,  f='wav', ac=1, ar=16000)
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        except Exception as e:
            s = f'ERROR while preparing audio: {e}'
            logging.error(s)
            return
        logging.info("Transcription...")
        try:
            full_translation = self.get_transcription(tmp_audio_path)
        except Exception as e:
            s = f'ERROR while transcript audio: {e}'
            logging.error(s)
            return

        self.write_translation(audio_file_name, full_translation)
        self.clean()
        done_time = time.time()
        logging.info(f'Done in {time.strftime("%H:%M:%S", time.gmtime(done_time - start_time))}\n')
        return
