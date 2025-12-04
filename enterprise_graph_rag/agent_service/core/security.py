import logging
from typing import List, Optional
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)

class SecurityManager:
    _instance = None
    
    def __init__(self):
        if SecurityManager._instance is not None:
            raise RuntimeError("Use get_instance()")
        
        logger.info("loading_presidio_nlp_engine")
        try:
            # Initialize Engines (loads spacy model)
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            
            # Define what we want to scrub
            self.entities_to_scrub = [
                "EMAIL_ADDRESS", 
                "PHONE_NUMBER", 
                "CREDIT_CARD", 
                "CRYPTO", 
                "IP_ADDRESS",
                "IBAN_CODE",
                "US_SSN"
            ]
            # Note: We exclude "PERSON" by default because asking 
            # "Who is Alice?" would become "Who is <REDACTED>?" which breaks the agent.
            
            SecurityManager._instance = self
            logger.info("presidio_loaded_successfully")
        except Exception as e:
            logger.error(f"failed_to_load_presidio: {e}")
            raise e

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls()
        return cls._instance

    def sanitize_input(self, text: str) -> str:
        """
        Analyzes and anonymizes PII from the input text.
        """
        if not text:
            return ""

        try:
            # 1. Analyze (Find PII)
            results = self.analyzer.analyze(
                text=text,
                entities=self.entities_to_scrub,
                language='en'
            )

            # 2. Anonymize (Replace PII)
            # We use 'replace' operator to swap with <ENTITY_TYPE>
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
                    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE_REDACTED>"}),
                    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL_REDACTED>"}),
                }
            )
            
            return anonymized_result.text

        except Exception as e:
            logger.error(f"pii_scrubbing_failed: {e}")
            # Fail open: Return original text so we don't block the user, 
            # but log the security failure.
            return text