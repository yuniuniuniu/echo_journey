import string
import time
import azure.cognitiveservices.speech as speechsdk

def pronunciation_assessment_continuous_from_file():
    """Performs continuous pronunciation assessment asynchronously with input from an audio file.
        See more information at https://aka.ms/csspeech/pa"""

    import difflib
    import json

    speech_config = speechsdk.SpeechConfig(subscription="73dbca97-37d0-462f-95da-9124ae577818 ", region="eastus")
    # provide a WAV file as an example. Replace it with your own.
    audio_config = speechsdk.audio.AudioConfig(filename="Sample_1.wav")

    reference_text = "你好啊，我在呢"
    # create pronunciation assessment config, set grading system, granularity and if enable miscue based on your requirement.
    enable_miscue = True
    enable_prosody_assessment = True
    pronunciation_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=enable_miscue)
    if enable_prosody_assessment:
        pronunciation_config.enable_prosody_assessment()

    # Creates a speech recognizer using a file as audio input.
    language = 'zh-CN'
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, language=language, audio_config=audio_config)
    # apply pronunciation assessment config to speech recognizer
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
    # stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # Start continuous pronunciation assessment
    speech_recognizer.start_continuous_recognition()
    while not done:
        time.sleep(.5)

    speech_recognizer.stop_continuous_recognition()

    # we need to convert the reference text to lower case, and split to words, then remove the punctuations.
    if language == 'zh-CN':
        # Use jieba package to split words for Chinese
        import jieba
        import zhon.hanzi
        jieba.suggest_freq([x.word for x in recognized_words], True)
        reference_words = [w for w in jieba.cut(reference_text) if w not in zhon.hanzi.punctuation]
    else:
        reference_words = [w.strip(string.punctuation) for w in reference_text.lower().split()]

    # For continuous pronunciation assessment mode, the service won't return the words with `Insertion` or `Omission`
    # even if miscue is enabled.
    # We need to compare with the reference text after received all recognized words to get these error words.
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

    # We can calculate whole accuracy by averaging
    final_accuracy_scores = []
    for word in final_words:
        if word.error_type == 'Insertion':
            continue
        else:
            final_accuracy_scores.append(word.accuracy_score)
    accuracy_score = sum(final_accuracy_scores) / len(final_accuracy_scores)
    # Re-calculate fluency score
    fluency_score = sum([x * y for (x, y) in zip(fluency_scores, durations)]) / sum(durations)
    # Calculate whole completeness score
    completeness_score = len([w for w in recognized_words if w.error_type == "None"]) / len(reference_words) * 100
    completeness_score = completeness_score if completeness_score <= 100 else 100
    # Re-calculate prosody score
    prosody_score = sum(prosody_scores) / len(prosody_scores)
    pron_score = accuracy_score * 0.4 + prosody_score * 0.2 + fluency_score * 0.2 + completeness_score * 0.2

    print('    Paragraph pronunciation score: {}, accuracy score: {}, completeness score: {}, fluency score: {}, prosody score: {}'.format(
        pron_score, accuracy_score, completeness_score, fluency_score, prosody_score
    ))

    for idx, word in enumerate(final_words):
        print('    {}: word: {}\taccuracy score: {}\terror type: {};'.format(
            idx + 1, word.word, word.accuracy_score, word.error_type
        ))
        
pronunciation_assessment_continuous_from_file()