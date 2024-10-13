import azure.cognitiveservices.speech as speechsdk
import string
import time

def pronunciation_assessment_continuous_from_bytes(wav_bytes):
    """Performs continuous pronunciation assessment asynchronously with input from a WAV byte stream."""

    import difflib
    import json
    # Creates an instance of a speech config with specified subscription key and service region.
    # Replace with your own subscription key and service region (e.g., "westus").
    speech_config = speechsdk.SpeechConfig(subscription="1ee42e99f7394ac4915f120ccfe9db73", region="eastus")
    # Create an audio stream from the wav bytes
    audio_stream = speechsdk.audio.PushAudioInputStream()
    stream_format = speechsdk.audio.AudioStreamFormat(16000, 16, 1)
    audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
    # Write WAV bytes to the stream
    audio_stream.write(wav_bytes)
    audio_stream.close()

    reference_text = "我想喝咖啡"
    
    enable_miscue = True
    enable_prosody_assessment = True
    pronunciation_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=enable_miscue)

    if enable_prosody_assessment:
        pronunciation_config.enable_prosody_assessment()

    language = 'zh-CN'
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, language=language, audio_config=audio_config)
    pronunciation_config.apply_to(speech_recognizer)

    done = False
    recognized_words = []
    fluency_scores = []
    prosody_scores = []
    durations = []

    def stop_cb(evt: speechsdk.SessionEventArgs):
        """callback that signals to stop continuous recognition upon receiving an event `evt`"""
        print('CLOSING on {}'.format(evt))
        nonlocal done
        done = True

    def recognized(evt: speechsdk.SpeechRecognitionEventArgs):
        print('pronunciation assessment for: {}'.format(evt.result.text))
        pronunciation_result = speechsdk.PronunciationAssessmentResult(evt.result)
        print('    Accuracy score: {}, pronunciation score: {}, completeness score : {}, fluency score: {}, prosody score: {}'.format(
            pronunciation_result.accuracy_score, pronunciation_result.pronunciation_score,
            pronunciation_result.completeness_score, pronunciation_result.fluency_score, pronunciation_result.prosody_score
        ))
        nonlocal recognized_words, fluency_scores, durations, prosody_scores
        recognized_words += pronunciation_result.words
        fluency_scores.append(pronunciation_result.fluency_score)
        prosody_scores.append(pronunciation_result.prosody_score)
        json_result = evt.result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        jo = json.loads(json_result)
        nb = jo['NBest'][0]
        durations.append(sum([int(w['Duration']) for w in nb['Words']]))

    # Connect callbacks to the events fired by the speech recognizer
    speech_recognizer.recognized.connect(recognized)
    speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
    speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    speech_recognizer.start_continuous_recognition()
    while not done:
        time.sleep(.5)

    speech_recognizer.stop_continuous_recognition()

    if language == 'zh-CN':
        import jieba
        import zhon.hanzi
        jieba.suggest_freq([x.word for x in recognized_words], True)
        reference_words = [w for w in jieba.cut(reference_text) if w not in zhon.hanzi.punctuation]
    else:
        reference_words = [w.strip(string.punctuation) for w in reference_text.lower().split()]

    if enable_miscue:
        diff = difflib.SequenceMatcher(None, reference_words, [x.word.lower() for x in recognized_words])
        final_words = []
        for tag, i1, i2, j1, j2 in diff.get_opcodes():
            if tag in ['insert', 'replace']:
                for word in recognized_words[j1:j2]:
                    if word.error_type == 'None':
                        word._error_type = 'Insertion'
                    final_words.append(word)
            if tag in ['delete', 'replace']:
                for word_text in reference_words[i1:i2]:
                    word = speechsdk.PronunciationAssessmentWordResult({
                        'Word': word_text,
                        'PronunciationAssessment': {
                            'ErrorType': 'Omission',
                        }
                    })
                    final_words.append(word)
            if tag == 'equal':
                final_words += recognized_words[j1:j2]
    else:
        final_words = recognized_words

    final_accuracy_scores = []
    for word in final_words:
        if word.error_type == 'Insertion':
            continue
        else:
            final_accuracy_scores.append(word.accuracy_score)
    accuracy_score = sum(final_accuracy_scores) / len(final_accuracy_scores)
    fluency_score = sum([x * y for (x, y) in zip(fluency_scores, durations)]) / sum(durations)
    completeness_score = len([w for w in recognized_words if w.error_type == "None"]) / len(reference_words) * 100
    completeness_score = completeness_score if completeness_score <= 100 else 100
    prosody_score = sum(prosody_scores) / len(prosody_scores)
    pron_score = accuracy_score * 0.4 + prosody_score * 0.2 + fluency_score * 0.2 + completeness_score * 0.2

    print('    Paragraph pronunciation score: {}, accuracy score: {}, completeness score: {}, fluency score: {}, prosody score: {}'.format(
        pron_score, accuracy_score, completeness_score, fluency_score, prosody_score
    ))

    for idx, word in enumerate(final_words):
        print('    {}: word: {}\taccuracy score: {}\terror type: {};'.format(
            idx + 1, word.word, word.accuracy_score, word.error_type
        ))

# Example usage with wav bytes
with open("/root/echo_journey/tests/data/啊微.wav", "rb") as f:
    wav_bytes = f.read()

pronunciation_assessment_continuous_from_bytes(wav_bytes)
