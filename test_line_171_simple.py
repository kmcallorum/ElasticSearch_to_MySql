"""
THE SIMPLEST TEST FOR LINE 171

Just patch is_alive() at the class level to FORCE line 171 execution.

Author: Kevin McAllorum
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from metrics_server import MetricsServer


class TestLine171Simple:
    """The simplest approach - patch at stop() call time"""
    
    def test_force_thread_join_line_171(self):
        """Force line 171 by patching is_alive during stop()"""
        server = MetricsServer(port=9900)
        server.start()
        time.sleep(0.2)
        
        # Ensure thread exists
        assert server.thread is not None
        
        # Patch the thread.is_alive method right before stop()
        # Make it return True so we enter the if block
        with patch.object(server.thread, 'is_alive', return_value=True):
            # Also patch join to make it quick (but it will still be called)
            with patch.object(server.thread, 'join') as mock_join:
                # Call stop - this will check is_alive() (returns True)
                # Then call join() at line 171
                server.stop()
                
                # Verify line 171 was hit
                mock_join.assert_called_once()
                
                # Check it was called with timeout
                args, kwargs = mock_join.call_args
                # Either timeout=5.0 in kwargs or 5.0 in args
                assert kwargs.get('timeout') == 5.0 or (len(args) > 0 and args[0] == 5.0)
    
    def test_line_171_direct_monkeypatch(self):
        """Directly monkeypatch to force line 171"""
        server = MetricsServer(port=9901)
        server.start()
        time.sleep(0.2)
        
        # Save original methods
        original_is_alive = server.thread.is_alive
        original_join = server.thread.join
        
        # Track if join was called
        join_called = [False]
        
        # Replace methods
        def force_alive():
            return True  # Always say alive
        
        def track_join(*args, **kwargs):
            join_called[0] = True
            # Don't actually join, just mark it
        
        server.thread.is_alive = force_alive
        server.thread.join = track_join
        
        try:
            # Stop server - should hit line 171
            server.stop()
            
            # Verify join was called
            assert join_called[0], "Line 171 was not hit!"
        finally:
            # Cleanup
            server.thread.is_alive = original_is_alive
            server.thread.join = original_join
    
    def test_line_171_absolute(self):
        """ABSOLUTE test - create fake thread that stays alive"""
        server = MetricsServer(port=9902)
        server.start()
        time.sleep(0.1)
        
        if server.thread and server._running:
            # Create a mock thread that reports as alive
            fake_thread = MagicMock()
            fake_thread.is_alive.return_value = True
            fake_thread.join = MagicMock()
            
            # Replace the actual thread with our fake one
            server.thread = fake_thread
            
            # Now stop - this MUST hit line 171
            server.stop()
            
            # Verify join was called
            fake_thread.join.assert_called_once_with(timeout=5.0)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v", "-s"])
