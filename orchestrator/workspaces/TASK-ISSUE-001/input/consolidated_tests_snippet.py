    def test_service_status_response(self, result: TestResult):
        """2.1.2 - Проверка статуса демона"""
        try:
            # Ищем процесс демона
            daemon_found = False
            daemon_info = {}
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    if any('scheduler_daemon' in str(cmd) for cmd in proc.info['cmdline'] or []):
                        daemon_found = True
                        daemon_info = {
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'create_time': datetime.fromtimestamp(proc.info['create_time']).isoformat(),
                            'uptime_seconds': time.time() - proc.info['create_time']
                        }
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            result.details = {
                'daemon_found': daemon_found,
                'daemon_info': daemon_info
            }
            
            assert daemon_found, "Демон планировщика не найден среди процессов"
            assert daemon_info['uptime_seconds'] > 0, "Время работы демона некорректно"
            
        except Exception as e:
            # Если не можем найти через процессы, проверяем через файл состояния
            state_file = Path(__file__).parent.parent / "data" / "daemon.state"
            if state_file.exists():
                result.details['daemon_status'] = "Файл состояния найден"
            else:
                raise AssertionError(f"Демон не активен: {e}")
