"""
Audio Classification Service using YAMNet
Classifies audio into content types: speech, song, poetry, instrumental, ambient, etc.
"""

import tensorflow as tf
import tensorflow_hub as hub
import librosa
import numpy as np
import logging
import csv
import urllib.request
from typing import Dict, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class YAMNetAudioClassifier:
    def __init__(self):
        self.model = None
        self.class_names = None
        self._load_model()
        self._setup_category_mappings()
    
    def _load_model(self):
        """Load YAMNet model from TensorFlow Hub"""
        try:
            logger.info("Loading YAMNet model from TensorFlow Hub...")
            self.model = hub.load('https://tfhub.dev/google/yamnet/1')
            
            # Get class names - they might be in different attributes
            if hasattr(self.model, 'class_names'):
                self.class_names = self.model.class_names
            elif hasattr(self.model, 'class_map_path'):
                # Load class names from CSV file
                import csv
                import urllib.request
                csv_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
                class_names = []
                try:
                    with urllib.request.urlopen(csv_url) as response:
                        csv_content = response.read().decode('utf-8')
                        csv_reader = csv.reader(csv_content.strip().split('\n'))
                        next(csv_reader)  # Skip header
                        for row in csv_reader:
                            if len(row) >= 3:
                                class_names.append(row[2])  # display_name column
                    self.class_names = tf.convert_to_tensor(class_names)
                except Exception as csv_e:
                    logger.warning(f"Could not load class names from CSV: {csv_e}")
                    # Fallback: create dummy class names
                    self.class_names = tf.convert_to_tensor([f"class_{i}" for i in range(521)])
            else:
                logger.warning("Class names not found in model, using dummy names")
                self.class_names = tf.convert_to_tensor([f"class_{i}" for i in range(521)])
            
            logger.info(f"YAMNet model loaded successfully. {len(self.class_names)} classes available.")
        except Exception as e:
            logger.error(f"Failed to load YAMNet model: {e}")
            raise

    def _setup_category_mappings(self):
        """Map YAMNet's 521 classes to our content categories"""
        
        # Define our target categories and their YAMNet class mappings
        self.category_mappings = {
            'speech': [
                'speech', 'conversation', 'narration', 'monologue', 'child speech',
                'baby laughter', 'babbling', 'speech synthesizer', 'male speech',
                'female speech', 'whispering', 'breathing', 'snoring', 'gasp',
                'inside, small room', 'inside, large room or hall', 'telephone bell ringing'
            ],
            
            'song': [
                'singing', 'vocal music', 'lullaby', 'humming', 'male singing',
                'female singing', 'child singing', 'choir', 'yodeling', 'chant',
                'mantra', 'rapping', 'hip hop music', 'pop music', 'rock music',
                'country music', 'blues', 'folk music', 'soul music', 'reggae',
                'latin music', 'ballad', 'opera', 'gospel music'
            ],
            
            'poetry': [
                'speech', 'narration', 'monologue', 'recitation', 'poetry reading',
                'spoken word', 'storytelling', 'radio', 'television'
            ],
            
            'instrumental': [
                'music', 'instrumental music', 'classical music', 'jazz', 'electronic music',
                'ambient music', 'new-age music', 'drum', 'piano', 'guitar', 'violin',
                'flute', 'trumpet', 'saxophone', 'orchestra', 'brass instrument',
                'string section', 'woodwind instrument', 'percussion', 'synthesizer',
                'electric guitar', 'bass guitar', 'drum kit', 'electronic organ',
                'harmonica', 'accordion', 'harp', 'banjo', 'mandolin', 'ukulele',
                'bagpipes', 'didgeridoo', 'timpani', 'xylophone', 'marimba',
                'bell', 'chime', 'gong', 'tuning fork'
            ],
            
            'ambient': [
                'ambient music', 'new-age music', 'environmental noise', 'wind noise',
                'rain', 'thunderstorm', 'water', 'stream', 'ocean', 'waves',
                'fire', 'crackling fire', 'bird', 'bird vocalization', 'bird song',
                'chirp', 'tweet', 'cricket', 'frog', 'insect', 'wind',
                'rustling leaves', 'mechanical fan', 'air conditioning',
                'white noise', 'pink noise', 'hum', 'buzz'
            ],
            
            'sound_effects': [
                'sound effect', 'whoosh', 'swoosh', 'beep', 'bleep', 'ding',
                'ping', 'buzz', 'hum', 'vibration', 'rumble', 'whir',
                'mechanical noise', 'static', 'crackle', 'hiss', 'pop',
                'bang', 'boom', 'crash', 'slam', 'thud', 'tap', 'knock'
            ],
            
            'noise': [
                'noise', 'static', 'white noise', 'pink noise', 'brown noise',
                'hiss', 'hum', 'buzz', 'crackle', 'pop', 'interference',
                'distortion', 'feedback'
            ],
            
            'animal_sounds': [
                'animal', 'domestic animals', 'pets', 'dog', 'bark', 'bow-wow',
                'cat', 'meow', 'purr', 'bird', 'rooster', 'chicken', 'cow',
                'moo', 'pig', 'oink', 'horse', 'neigh', 'sheep', 'bleat',
                'goat', 'duck', 'quack', 'goose', 'honk', 'turkey'
            ],
            
            'mechanical': [
                'mechanism', 'motor', 'engine', 'car', 'vehicle', 'truck',
                'motorcycle', 'airplane', 'helicopter', 'train', 'boat',
                'ship', 'industrial noise', 'machinery', 'tools',
                'power tool', 'drill', 'saw', 'hammer', 'construction noise'
            ]
        }
        
        # Create reverse mapping for faster lookup
        self.class_to_category = {}
        for category, class_keywords in self.category_mappings.items():
            for keyword in class_keywords:
                self.class_to_category[keyword.lower()] = category

    def classify_audio(self, audio_file_path: str) -> Dict:
        """
        Classify audio file using YAMNet directly
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Dict with classification results
        """
        try:
            logger.info(f"Classifying audio: {audio_file_path}")
            
            # Load and preprocess audio
            audio_data, sample_rate = librosa.load(audio_file_path, sr=16000, mono=True)
            
            if len(audio_data) == 0:
                return self._create_error_result("Empty audio file")
            
            # Get YAMNet predictions
            scores, embeddings, spectrogram = self.model(audio_data)
            
            # Average predictions across time segments
            mean_scores = tf.reduce_mean(scores, axis=0)
            
            # Get top predictions
            top_k = 10
            top_indices = tf.nn.top_k(mean_scores, k=top_k).indices
            
            # Get class names and scores
            predictions = []
            for i, idx in enumerate(top_indices):
                class_name = self.class_names[idx].numpy().decode('utf-8')
                confidence = float(mean_scores[idx].numpy())
                predictions.append((class_name, confidence))
            
            # Use YAMNet's top prediction directly
            top_prediction = predictions[0]
            primary_class = top_prediction[0]
            primary_confidence = top_prediction[1]
            
            # Always transcribe - let the content speak for itself
            should_transcribe = True
            processing_recommendation = 'transcribe_and_classify'
            
            # Create result using YAMNet's classification directly
            result = {
                'primary_class': primary_class,
                'confidence': primary_confidence,
                'top_yamnet_predictions': predictions,
                'processing_recommendation': processing_recommendation,
                'should_transcribe': should_transcribe,
                'file_path': audio_file_path,
                'audio_duration': len(audio_data) / sample_rate
            }
            
            logger.info(f"Classification complete: {primary_class} (confidence: {primary_confidence:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"Error classifying audio {audio_file_path}: {e}")
            return self._create_error_result(str(e))

    def _should_transcribe_yamnet_class(self, yamnet_class: str) -> bool:
        """Determine if audio should be transcribed based on YAMNet's classification"""
        
        class_lower = yamnet_class.lower()
        
        # Always transcribe speech and vocal content
        speech_keywords = ['speech', 'conversation', 'narration', 'monologue', 'talking', 'voice']
        vocal_keywords = ['singing', 'vocal', 'choir', 'chant', 'humming', 'rapping']
        
        # Check for speech
        if any(keyword in class_lower for keyword in speech_keywords):
            return True
            
        # Check for vocal/singing content (songs with lyrics)
        if any(keyword in class_lower for keyword in vocal_keywords):
            return True
            
        # Music could have lyrics, so transcribe by default unless clearly instrumental
        if 'music' in class_lower:
            # Don't transcribe if clearly instrumental
            instrumental_keywords = ['piano', 'guitar', 'violin', 'drum', 'trumpet', 'saxophone', 
                                   'orchestra', 'instrumental', 'organ', 'flute', 'clarinet']
            if any(keyword in class_lower for keyword in instrumental_keywords):
                return False
            else:
                # Generic "music" - could have vocals, so transcribe to be safe
                return True
        
        # Don't transcribe other sounds
        return False

    def _semantic_category_match(self, class_name: str) -> List[str]:
        """Semantic matching for classes not in our explicit mappings"""
        
        matches = []
        
        # Speech-related keywords
        if any(word in class_name for word in ['talk', 'speak', 'voice', 'conversation', 'discussion']):
            matches.append('speech')
        
        # Music-related keywords
        if any(word in class_name for word in ['music', 'melody', 'harmony', 'rhythm', 'beat']):
            matches.append('instrumental')
        
        # Vocal music keywords
        if any(word in class_name for word in ['sing', 'vocal', 'choir', 'verse', 'chorus']):
            matches.append('song')
        
        # Nature/ambient keywords
        if any(word in class_name for word in ['nature', 'outdoor', 'environment', 'atmosphere']):
            matches.append('ambient')
        
        # Mechanical keywords
        if any(word in class_name for word in ['machine', 'engine', 'motor', 'mechanical', 'device']):
            matches.append('mechanical')
        
        return matches

    def _get_processing_recommendation(self, category_result: Dict) -> str:
        """Recommend processing method based on classification"""
        
        primary_category = category_result['primary_category']
        confidence = category_result['confidence']
        
        if confidence < 0.3:
            return 'manual_review'
        
        processing_map = {
            'speech': 'standard_transcription',
            'song': 'creative_preserve',
            'poetry': 'artistic_transcription',
            'instrumental': 'music_metadata_only',
            'ambient': 'ambient_preserve',
            'sound_effects': 'effects_metadata',
            'noise': 'noise_filter',
            'animal_sounds': 'nature_preserve',
            'mechanical': 'environmental_log'
        }
        
        return processing_map.get(primary_category, 'standard_transcription')

    def _should_transcribe(self, category: str) -> bool:
        """Determine if audio should be transcribed based on category"""
        
        transcribe_categories = {'speech', 'poetry'}
        return category in transcribe_categories

    def _create_error_result(self, error_message: str) -> Dict:
        """Create error result structure"""
        return {
            'primary_category': 'error',
            'confidence': 0.0,
            'category_scores': {},
            'top_yamnet_predictions': [],
            'processing_recommendation': 'manual_review',
            'should_transcribe': False,
            'error': error_message,
            'file_path': None,
            'audio_duration': 0.0
        }

    def get_category_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all categories"""
        return {
            'speech': 'Spoken conversation, narration, monologue, or dialogue',
            'song': 'Vocal music with singing, including all music genres with vocals',
            'poetry': 'Spoken word, poetry reading, recitation, or artistic speech',
            'instrumental': 'Music without vocals, including all instrumental genres',
            'ambient': 'Environmental sounds, nature sounds, or ambient music',
            'sound_effects': 'Artificial sounds, beeps, mechanical noises, or audio effects',
            'noise': 'Background noise, static, hiss, or unwanted audio artifacts',
            'animal_sounds': 'Animal vocalizations, pet sounds, or wildlife audio',
            'mechanical': 'Vehicle sounds, machinery, tools, or industrial noise'
        }

    def batch_classify(self, audio_files: List[str]) -> Dict[str, Dict]:
        """Classify multiple audio files"""
        results = {}
        
        for audio_file in audio_files:
            try:
                results[audio_file] = self.classify_audio(audio_file)
            except Exception as e:
                logger.error(f"Failed to classify {audio_file}: {e}")
                results[audio_file] = self._create_error_result(str(e))
        
        return results

    def get_classification_summary(self, results: Dict) -> Dict:
        """Generate summary statistics from classification results"""
        if isinstance(results, dict) and 'primary_category' in results:
            # Single result
            results = {'single_file': results}
        
        summary = {
            'total_files': len(results),
            'category_counts': {},
            'avg_confidence': 0.0,
            'processing_recommendations': {}
        }
        
        confidences = []
        
        for file_path, result in results.items():
            if result.get('primary_category') != 'error':
                category = result['primary_category']
                summary['category_counts'][category] = summary['category_counts'].get(category, 0) + 1
                
                confidence = result.get('confidence', 0.0)
                confidences.append(confidence)
                
                processing = result.get('processing_recommendation', 'unknown')
                summary['processing_recommendations'][processing] = summary['processing_recommendations'].get(processing, 0) + 1
        
        if confidences:
            summary['avg_confidence'] = sum(confidences) / len(confidences)
        
        return summary


# Convenience function for easy import
def classify_audio_file(audio_file_path: str) -> Dict:
    """Convenience function to classify a single audio file"""
    classifier = YAMNetAudioClassifier()
    return classifier.classify_audio(audio_file_path)


if __name__ == "__main__":
    # Test the classifier
    import sys
    
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        result = classify_audio_file(audio_file)
        print(f"\nAudio Classification Results for: {audio_file}")
        print(f"Primary Category: {result['primary_category']}")
        print(f"Confidence: {result['confidence']:.3f}")
        print(f"Should Transcribe: {result['should_transcribe']}")
        print(f"Processing Recommendation: {result['processing_recommendation']}")
        print(f"\nTop YAMNet Predictions:")
        for i, (class_name, conf) in enumerate(result['top_yamnet_predictions'][:5], 1):
            print(f"  {i}. {class_name}: {conf:.3f}")
    else:
        print("Usage: python audio_classifier.py <audio_file_path>")