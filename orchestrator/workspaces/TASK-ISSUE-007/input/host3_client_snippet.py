        self.config = config
        self.api_endpoint = config.get('api_endpoint', 'http://localhost:8000/v1')
        self.api_key = config.get('api_key', 'mock_api_key')
        self.default_model = config.get('default_model', 'gpt-3.5-turbo')
        self.mock_mode = config.get('mock_mode', True)  # В MVP всегда True
        self.timeout = config.get('timeout', 30)
        
        self._request_count = 0
        self._last_request = None
        
        logger.info(f"LLMClient initialized: {self.api_endpoint}")
        if self.mock_mode:
            logger.info("LLM client running in MOCK MODE")
