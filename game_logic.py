from random import shuffle, choice
from flask import session

class LanguageGame:
    def __init__(self):
        self.phrases = {
            1: [
                {"id": 1, "local": "வணக்கம்", "translation": "Hello", "audio": "vanakkam.mp3"},
                {"id": 2, "local": "நன்றி", "translation": "Thank you", "audio": "nandri.mp3"},
                {"id": 3, "local": "பிறகு பார்க்கலாம்", "translation": "See you later", "audio": "piragu.mp3"},
                {"id": 4, "local": "எப்படி இருக்கிறீர்கள்", "translation": "How are you", "audio": "eppadi.mp3"},
            ],
            2: [
                {"id": 5, "local": "காலை வணக்கம்", "translation": "Good morning", "audio": "kalai.mp3"},
                {"id": 6, "local": "மாலை வணக்கம்", "translation": "Good evening", "audio": "malai.mp3"},
                {"id": 7, "local": "சாப்பிட்டீர்களா", "translation": "Have you eaten", "audio": "saapitingala.mp3"},
                {"id": 8, "local": "என் பெயர்", "translation": "My name is", "audio": "enpeyar.mp3"},
            ],
            3: [
                {"id": 9, "local": "எனக்கு தமிழ் தெரியும்", "translation": "I know Tamil", "audio": "enakku.mp3"},
                {"id": 10, "local": "உங்களுக்கு புரிகிறதா", "translation": "Do you understand", "audio": "ungalukku.mp3"},
                {"id": 11, "local": "மீண்டும் சொல்லுங்கள்", "translation": "Please repeat", "audio": "meendum.mp3"},
                {"id": 12, "local": "மெதுவாக பேசுங்கள்", "translation": "Please speak slowly", "audio": "methuvaga.mp3"},
            ]
        }

    def get_game_state(self):
        return {
            'level': session.get('level', 1),
            'lives': session.get('lives', 3),
            'streak': session.get('streak', 0)
        }

    def get_current_phrase(self):
        level = session.get('level', 1)
        available_phrases = self.phrases.get(level, [])
        current_phrase = choice(available_phrases)
        options = self.generate_options(current_phrase, available_phrases)
        
        return {
            'phrase': current_phrase,
            'options': options
        }

    def generate_options(self, current_phrase, available_phrases):
        options = [current_phrase['translation']]
        other_phrases = [p for p in available_phrases if p['id'] != current_phrase['id']]
        
        while len(options) < 4 and other_phrases:
            random_phrase = choice(other_phrases)
            options.append(random_phrase['translation'])
            other_phrases.remove(random_phrase)
        
        shuffle(options)
        return options

    def check_answer(self, selected_answer, correct_answer):
        if selected_answer == correct_answer:
            session['streak'] = session.get('streak', 0) + 1
            completed_level = session['streak'] >= 5
            
            if completed_level:
                return self.complete_level()
            
            return {'success': True, 'completed_level': False}
        else:
            session['lives'] = session.get('lives', 3) - 1
            session['streak'] = 0
            
            if session['lives'] <= 0:
                self.reset_game()
                return {'success': False, 'game_over': True}
            
            return {'success': False, 'game_over': False}

    def complete_level(self):
        current_level = session.get('level', 1)
        badge = {
            'id': f'level_{current_level}',
            'title': f'Language Master Level {current_level}',
            'image': f'badge{current_level}.png'
        }
        
        session['level'] = current_level + 1
        session['streak'] = 0
        
        return {
            'success': True,
            'completed_level': True,
            'badge': badge
        }

    def reset_game(self):
        session['level'] = 1
        session['lives'] = 3
        session['streak'] = 0