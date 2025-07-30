"""
Audio Service - All audio processing operations
Handles transcription, metadata extraction, and audio format operations
"""

import speech_recognition as sr
import subprocess
import tempfile
import os
from pydub import AudioSegment
from pydub.utils import which
import logging
from mutagen import File
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Check if ffmpeg is available for audio conversion
        AudioSegment.converter = which("ffmpeg")
        AudioSegment.ffmpeg = which("ffmpeg")
        AudioSegment.ffprobe = which("ffprobe")
    
    def transcribe_audio(self, audio_file_path: str, use_whisper_first: bool = True) -> str:
        """
        Main transcription method that tries different approaches
        """
        logger.info(f"Transcribing: {audio_file_path}")
        
        if use_whisper_first:
            # Try Whisper first (better quality, works offline)
            transcript = self._transcribe_with_whisper_local(audio_file_path)
            if transcript:
                logger.info("Successfully transcribed with Whisper")
                return transcript
            
            logger.info("Whisper not available, trying Google...")
        
        # Fallback to Google speech recognition
        transcript = self._transcribe_with_google(audio_file_path)
        if transcript:
            logger.info("Successfully transcribed with Google speech recognition")
            return transcript
        
        logger.error("All transcription methods failed")
        return None
    
    def _transcribe_with_whisper_local(self, audio_file_path: str) -> str:
        """
        Use OpenAI Whisper locally (if installed) with chunking for long files
        This requires: pip install openai-whisper
        """
        try:
            import whisper
            from pydub import AudioSegment
            import tempfile
            import math
            
            # Load Whisper model (downloads on first use - about 244MB for base model)
            model = whisper.load_model("base")  # Options: tiny, base, small, medium, large
            
            # Check audio duration first
            try:
                audio_segment = AudioSegment.from_file(audio_file_path)
                duration_minutes = len(audio_segment) / (1000 * 60)  # Convert ms to minutes
                logger.info(f"Audio duration: {duration_minutes:.1f} minutes")
                
                # If audio is longer than 15 minutes, chunk it to avoid timeouts
                if duration_minutes > 15:
                    logger.info("Long audio detected, using chunking approach")
                    return self._transcribe_long_audio_chunked(model, audio_segment)
                else:
                    # For shorter audio, transcribe directly
                    result = model.transcribe(audio_file_path, fp16=False)
                    return result["text"].strip()
                    
            except Exception as e:
                logger.warning(f"Could not determine audio duration, trying direct transcription: {e}")
                # Fallback to direct transcription
                result = model.transcribe(audio_file_path, fp16=False)
                return result["text"].strip()
            
        except ImportError:
            logger.info("Whisper not installed. Use: pip install openai-whisper")
            return None
        except Exception as e:
            logger.error(f"Error in Whisper transcription: {e}")
            # If Whisper fails, it might be due to audio format
            if "ffmpeg" in str(e).lower():
                logger.error("Whisper needs ffmpeg for this audio format. Install with: brew install ffmpeg")
            return None

    def _transcribe_long_audio_chunked(self, model, audio_segment):
        """
        Transcribe long audio by splitting into chunks
        """
        try:
            # Split into 10-minute chunks with 30-second overlap
            chunk_length_ms = 10 * 60 * 1000  # 10 minutes in milliseconds
            overlap_ms = 30 * 1000  # 30 seconds overlap
            
            chunks = []
            start_time = 0
            
            while start_time < len(audio_segment):
                end_time = min(start_time + chunk_length_ms, len(audio_segment))
                chunk = audio_segment[start_time:end_time]
                chunks.append(chunk)
                
                # Move start time for next chunk (with overlap)
                start_time = end_time - overlap_ms
                if start_time >= len(audio_segment) - overlap_ms:
                    break
            
            logger.info(f"Processing {len(chunks)} audio chunks")
            
            # Transcribe each chunk
            full_transcript = []
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"Transcribing chunk {i}/{len(chunks)}")
                
                # Save chunk to temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                temp_file.close()
                
                try:
                    chunk.export(temp_file.name, format="wav")
                    
                    # Transcribe chunk with timeout handling
                    result = model.transcribe(temp_file.name, fp16=False)
                    chunk_text = result["text"].strip()
                    
                    if chunk_text:
                        full_transcript.append(chunk_text)
                        
                except Exception as e:
                    logger.warning(f"Failed to transcribe chunk {i}: {e}")
                    # Continue with other chunks
                    
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
            
            if full_transcript:
                # Join chunks and clean up overlapping content
                combined_transcript = " ".join(full_transcript)
                return self._clean_overlapping_transcript(combined_transcript)
            else:
                logger.error("No chunks were successfully transcribed")
                return None
                
        except Exception as e:
            logger.error(f"Error in chunked transcription: {e}")
            return None

    def _clean_overlapping_transcript(self, transcript: str) -> str:
        """
        Clean up overlapping content from chunked transcription
        This is a simple approach - more sophisticated methods could be implemented
        """
        # Split into sentences
        sentences = transcript.split('.')
        
        # Simple deduplication: remove sentences that appear to be duplicates
        cleaned_sentences = []
        seen_sentences = set()
        
        for sentence in sentences:
            # Normalize sentence for comparison
            normalized = sentence.strip().lower()
            
            # Skip very short fragments and duplicates
            if len(normalized) > 10 and normalized not in seen_sentences:
                cleaned_sentences.append(sentence.strip())
                seen_sentences.add(normalized)
        
        return '. '.join(cleaned_sentences) + '.' if cleaned_sentences else transcript
    
    def _transcribe_with_google(self, audio_file_path: str) -> str:
        """
        Fallback transcription using Google Speech Recognition
        """
        try:
            # Convert to WAV format for speech recognition
            temp_wav = self._convert_to_wav(audio_file_path)
            
            with sr.AudioFile(temp_wav) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.record(source)
            
            # Use Google's free speech recognition
            text = self.recognizer.recognize_google(audio)
            return text
            
        except sr.UnknownValueError:
            logger.warning("Google Speech Recognition could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Could not request results from Google Speech Recognition: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in Google speech recognition: {e}")
            return None
        finally:
            # Clean up temporary file
            if 'temp_wav' in locals() and os.path.exists(temp_wav):
                os.unlink(temp_wav)
    
    def _convert_to_wav(self, audio_file_path: str) -> str:
        """
        Convert audio file to WAV format for processing
        """
        try:
            # Load audio file
            audio = AudioSegment.from_file(audio_file_path)
            
            # Convert to mono and set sample rate to 16kHz (optimal for speech recognition)
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            # Create temporary WAV file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()
            
            # Export as WAV
            audio.export(temp_file.name, format="wav")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error converting audio to WAV: {e}")
            raise
    
    def get_audio_metadata(self, audio_file_path: str) -> dict:
        """
        Extract audio metadata including duration, file size, creation date
        """
        try:
            file_path = Path(audio_file_path)
            
            # Basic file metadata
            stat = file_path.stat()
            metadata = {
                'file_size': stat.st_size,
                'file_created': datetime.fromtimestamp(stat.st_ctime),
                'file_modified': datetime.fromtimestamp(stat.st_mtime),
                'duration_seconds': 0.0
            }
            
            # Try to get audio duration using mutagen
            try:
                audio_file = File(audio_file_path)
                if audio_file and audio_file.info:
                    metadata['duration_seconds'] = float(audio_file.info.length)
                else:
                    # Fallback to pydub for duration
                    try:
                        audio_segment = AudioSegment.from_file(audio_file_path)
                        metadata['duration_seconds'] = len(audio_segment) / 1000.0  # Convert ms to seconds
                    except Exception:
                        logger.warning(f"Could not determine duration for {audio_file_path}")
            except Exception as e:
                logger.warning(f"Error reading audio metadata: {e}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting audio metadata: {e}")
            return {
                'file_size': 0,
                'file_created': None,
                'file_modified': None,
                'duration_seconds': 0.0
            }