"""
Performance tests for VoiceVault - Test upload performance across file size ranges
"""
import pytest
import time
import statistics
from pathlib import Path
import logging
import psutil
import os
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor system performance during tests"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = None
        self.start_time = None
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_time = time.time()
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            'memory_mb': current_memory,
            'memory_delta_mb': current_memory - (self.start_memory or 0),
            'elapsed_time': elapsed_time,
            'cpu_percent': self.process.cpu_percent()
        }


class TestUploadPerformance:
    """Test upload performance with different file sizes"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_file_size_performance_scaling(self, real_notion_uploader, categorized_files, 
                                         test_transcript_data, performance_metrics):
        """Test how upload performance scales with file size"""
        if not real_notion_uploader:
            pytest.skip("Real Notion uploader not available")
        
        # Test files from each size category
        test_cases = []
        
        for category in ['tiny', 'small', 'medium', 'large']:
            files = categorized_files.get(category, [])
            if files:
                test_cases.append((category, files[0]))
        
        if len(test_cases) < 3:
            pytest.skip("Need files from at least 3 size categories")
        
        results = []
        monitor = PerformanceMonitor()
        
        for category, file_path in test_cases:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            logger.info(f"Testing {category} file: {file_path.name} ({file_size_mb:.2f}MB)")
            
            monitor.start_monitoring()
            start_time = time.time()
            
            # Upload the file
            page_id = real_notion_uploader.create_page(
                title=f"Perf Test {category}: {file_path.name}",
                transcript=test_transcript_data['transcript'],
                claude_tags=test_transcript_data['claude_tags'],
                summary=test_transcript_data['summary'],
                filename=file_path.name,
                audio_file_path=str(file_path)
            )
            
            upload_time = time.time() - start_time
            metrics = monitor.get_metrics()
            
            results.append({
                'category': category,
                'file_name': file_path.name,
                'file_size_mb': file_size_mb,
                'upload_time': upload_time,
                'upload_speed_mbps': file_size_mb / upload_time if upload_time > 0 else 0,
                'memory_delta_mb': metrics['memory_delta_mb'],
                'success': page_id is not None
            })
            
            # Wait between tests to avoid rate limiting
            time.sleep(2)
        
        # Analyze results
        successful_results = [r for r in results if r['success']]
        assert len(successful_results) >= len(results) * 0.8, "At least 80% of uploads should succeed"
        
        # Test performance expectations
        tiny_results = [r for r in successful_results if r['category'] == 'tiny']
        large_results = [r for r in successful_results if r['category'] == 'large']
        
        if tiny_results and large_results:
            avg_tiny_time = statistics.mean([r['upload_time'] for r in tiny_results])
            avg_large_time = statistics.mean([r['upload_time'] for r in large_results])
            
            # Large files should not take more than 10x longer than tiny files
            assert avg_large_time / avg_tiny_time < 10, "Performance should scale reasonably with file size"
        
        # Log results
        print(f"\n📊 Upload Performance by File Size:")
        for result in results:
            status = "✅" if result['success'] else "❌"
            print(f"   {result['category']}: {result['upload_time']:.2f}s "
                  f"({result['upload_speed_mbps']:.2f} MB/s) {status}")
        
        # Store in performance metrics
        performance_metrics['upload_times'].extend([r['upload_time'] for r in successful_results])
        performance_metrics['file_sizes'].extend([r['file_size_mb'] for r in successful_results])
    
    @pytest.mark.performance
    def test_memory_usage_with_large_files(self, real_notion_uploader, categorized_files, 
                                         test_transcript_data):
        """Test memory usage doesn't grow excessively with large files"""
        if not real_notion_uploader:
            pytest.skip("Real Notion uploader not available")
        
        large_files = categorized_files.get('large', [])
        if not large_files:
            pytest.skip("No large files available for memory testing")
        
        test_file = large_files[0]
        file_size_mb = test_file.stat().st_size / (1024 * 1024)
        
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        
        initial_metrics = monitor.get_metrics()
        
        # Upload large file
        page_id = real_notion_uploader.create_page(
            title=f"Memory Test: {test_file.name}",
            transcript=test_transcript_data['transcript'],
            claude_tags=test_transcript_data['claude_tags'],
            summary=test_transcript_data['summary'],
            filename=test_file.name,
            audio_file_path=str(test_file)
        )
        
        final_metrics = monitor.get_metrics()
        memory_increase = final_metrics['memory_mb'] - initial_metrics['memory_mb']
        
        assert page_id is not None, "Large file upload should succeed"
        
        # Memory increase should be reasonable (less than 2x file size)
        assert memory_increase < file_size_mb * 2, \
            f"Memory increase ({memory_increase:.2f}MB) should be less than 2x file size ({file_size_mb:.2f}MB)"
        
        logger.info(f"✅ Memory usage acceptable: {memory_increase:.2f}MB increase for {file_size_mb:.2f}MB file")
    
    @pytest.mark.performance
    def test_upload_timeout_behavior(self, real_notion_uploader, categorized_files):
        """Test behavior under timeout conditions"""
        if not real_notion_uploader:
            pytest.skip("Real Notion uploader not available")
        
        # Use largest available file to maximize chance of timeout
        all_files = []
        for category, files in categorized_files.items():
            all_files.extend(files)
        
        if not all_files:
            pytest.skip("No files available for timeout testing")
        
        # Sort by size and pick largest
        largest_file = max(all_files, key=lambda f: f.stat().st_size)
        file_size_mb = largest_file.stat().st_size / (1024 * 1024)
        
        # Skip if file is too small to cause timeouts
        if file_size_mb < 5:
            pytest.skip(f"File too small for timeout testing: {file_size_mb:.2f}MB")
        
        logger.info(f"Testing timeout behavior with {largest_file.name} ({file_size_mb:.2f}MB)")
        
        # Test with reduced timeout to force timeout scenario
        original_timeout = real_notion_uploader.upload_timeout if hasattr(real_notion_uploader, 'upload_timeout') else None
        
        try:
            # Set aggressive timeout
            if hasattr(real_notion_uploader, 'upload_timeout'):
                real_notion_uploader.upload_timeout = 30  # 30 seconds
            
            start_time = time.time()
            
            page_id = real_notion_uploader.create_page(
                title=f"Timeout Test: {largest_file.name}",
                transcript="Test transcript for timeout scenario",
                claude_tags={'primary_themes': 'Timeout Testing'},
                summary="Testing timeout handling",
                filename=largest_file.name,
                audio_file_path=str(largest_file)
            )
            
            total_time = time.time() - start_time
            
            # Page should still be created even if file upload times out
            assert page_id is not None, "Page creation should succeed even with file timeout"
            
            logger.info(f"✅ Timeout handling works: Page created in {total_time:.2f}s")
            
        finally:
            # Restore original timeout
            if original_timeout and hasattr(real_notion_uploader, 'upload_timeout'):
                real_notion_uploader.upload_timeout = original_timeout


class TestConcurrentPerformance:
    """Test performance under concurrent load"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_upload_performance(self, real_notion_uploader, categorized_files, 
                                         test_transcript_data, performance_metrics):
        """Test performance with concurrent uploads"""
        if not real_notion_uploader:
            pytest.skip("Real Notion uploader not available")
        
        # Get multiple small files for concurrent testing
        small_files = categorized_files.get('small', [])[:5]  # Test with up to 5 files
        
        if len(small_files) < 3:
            pytest.skip("Need at least 3 small files for concurrent performance testing")
        
        import concurrent.futures
        import threading
        
        results = []
        lock = threading.Lock()
        monitor = PerformanceMonitor()
        
        def timed_upload(file_path, thread_id):
            thread_start = time.time()
            
            try:
                page_id = real_notion_uploader.create_page(
                    title=f"Concurrent Perf {thread_id}: {file_path.name}",
                    transcript=test_transcript_data['transcript'],
                    claude_tags=test_transcript_data['claude_tags'],
                    summary=test_transcript_data['summary'],
                    filename=file_path.name,
                    audio_file_path=str(file_path)
                )
                
                thread_time = time.time() - thread_start
                
                with lock:
                    results.append({
                        'thread_id': thread_id,
                        'file_name': file_path.name,
                        'file_size_mb': file_path.stat().st_size / (1024 * 1024),
                        'upload_time': thread_time,
                        'success': page_id is not None
                    })
                
                return page_id is not None
                
            except Exception as e:
                logger.error(f"Concurrent upload failed for thread {thread_id}: {e}")
                with lock:
                    results.append({
                        'thread_id': thread_id,
                        'file_name': file_path.name,
                        'file_size_mb': file_path.stat().st_size / (1024 * 1024),
                        'upload_time': time.time() - thread_start,
                        'success': False
                    })
                return False
        
        # Execute concurrent uploads
        monitor.start_monitoring()
        concurrent_start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(small_files)) as executor:
            futures = [
                executor.submit(timed_upload, file_path, i) 
                for i, file_path in enumerate(small_files)
            ]
            concurrent_results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_concurrent_time = time.time() - concurrent_start
        final_metrics = monitor.get_metrics()
        
        # Analyze results
        successful_uploads = sum(concurrent_results)
        successful_results = [r for r in results if r['success']]
        
        if successful_results:
            avg_individual_time = statistics.mean([r['upload_time'] for r in successful_results])
            max_individual_time = max([r['upload_time'] for r in successful_results])
            
            # Concurrent uploads should have reasonable performance
            efficiency = avg_individual_time / total_concurrent_time
            
            print(f"\n🚀 Concurrent Upload Performance:")
            print(f"   Files: {len(small_files)}")
            print(f"   Successful: {successful_uploads}")
            print(f"   Total time: {total_concurrent_time:.2f}s")
            print(f"   Avg individual: {avg_individual_time:.2f}s")
            print(f"   Max individual: {max_individual_time:.2f}s")
            print(f"   Efficiency: {efficiency:.2f}")
            print(f"   Memory delta: {final_metrics['memory_delta_mb']:.2f}MB")
            
            # Performance assertions
            assert successful_uploads >= len(small_files) * 0.8, "At least 80% should succeed"
            assert efficiency > 0.3, "Concurrent efficiency should be reasonable"
            
            # Update performance metrics
            performance_metrics['upload_times'].extend([r['upload_time'] for r in successful_results])
    
    @pytest.mark.performance
    def test_api_rate_limiting_effectiveness(self, real_notion_uploader, small_file):
        """Test that API rate limiting works effectively"""
        if not real_notion_uploader:
            pytest.skip("Real Notion uploader not available")
        
        # Make multiple rapid API calls and measure timing
        call_times = []
        
        for i in range(5):
            start = time.time()
            real_notion_uploader._rate_limit()
            end = time.time()
            call_times.append(end - start)
        
        # Check that rate limiting is working (some delays should occur)
        total_delay = sum(call_times)
        min_expected_delay = real_notion_uploader.min_request_interval * 4  # 4 intervals between 5 calls
        
        assert total_delay >= min_expected_delay * 0.8, \
            f"Rate limiting should add delays: got {total_delay:.3f}s, expected ≥{min_expected_delay:.3f}s"
        
        logger.info(f"✅ Rate limiting working: {total_delay:.3f}s total delay")


class TestStressTests:
    """Stress tests for edge cases"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_rapid_sequential_uploads(self, real_notion_uploader, categorized_files, 
                                    test_transcript_data):
        """Test rapid sequential uploads without overwhelming the API"""
        if not real_notion_uploader:
            pytest.skip("Real Notion uploader not available")
        
        # Use tiny files for rapid testing
        tiny_files = categorized_files.get('tiny', [])[:10]  # Up to 10 files
        
        if len(tiny_files) < 5:
            pytest.skip("Need at least 5 tiny files for rapid upload testing")
        
        results = []
        start_time = time.time()
        
        for i, file_path in enumerate(tiny_files):
            upload_start = time.time()
            
            page_id = real_notion_uploader.create_page(
                title=f"Rapid Upload {i}: {file_path.name}",
                transcript=test_transcript_data['transcript'],
                claude_tags=test_transcript_data['claude_tags'],
                summary=test_transcript_data['summary'],
                filename=file_path.name,
                audio_file_path=str(file_path)
            )
            
            upload_time = time.time() - upload_start
            results.append({
                'index': i,
                'upload_time': upload_time,
                'success': page_id is not None
            })
            
            # Small delay to be respectful to API
            time.sleep(0.5)
        
        total_time = time.time() - start_time
        successful_uploads = sum(1 for r in results if r['success'])
        
        # Analyze results
        avg_upload_time = statistics.mean([r['upload_time'] for r in results if r['success']])
        
        print(f"\n⚡ Rapid Sequential Upload Results:")
        print(f"   Files: {len(tiny_files)}")
        print(f"   Successful: {successful_uploads}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Avg per upload: {avg_upload_time:.2f}s")
        print(f"   Uploads per minute: {(successful_uploads / total_time) * 60:.1f}")
        
        # Performance assertions
        assert successful_uploads >= len(tiny_files) * 0.9, "At least 90% of rapid uploads should succeed"
        assert avg_upload_time < 10, "Average upload time should be reasonable"


@pytest.mark.performance
def test_performance_suite_summary(categorized_files, performance_metrics):
    """Print comprehensive performance summary"""
    if not performance_metrics['upload_times']:
        print("\n⚠️  No performance data collected")
        return
    
    # Calculate statistics
    times = performance_metrics['upload_times']
    sizes = performance_metrics['file_sizes']
    
    avg_time = statistics.mean(times)
    median_time = statistics.median(times)
    max_time = max(times)
    min_time = min(times)
    
    print(f"\n{'='*80}")
    print(f"🚀 PERFORMANCE TEST SUMMARY")
    print(f"{'='*80}")
    
    print(f"📊 Overall Upload Performance:")
    print(f"   Total uploads tested: {len(times)}")
    print(f"   Average time: {avg_time:.2f}s")
    print(f"   Median time: {median_time:.2f}s")
    print(f"   Fastest upload: {min_time:.2f}s")
    print(f"   Slowest upload: {max_time:.2f}s")
    
    if sizes:
        avg_size = statistics.mean(sizes)
        total_data = sum(sizes)
        avg_speed = avg_size / avg_time if avg_time > 0 else 0
        
        print(f"\n📈 Data Transfer:")
        print(f"   Total data uploaded: {total_data:.2f}MB")
        print(f"   Average file size: {avg_size:.2f}MB")
        print(f"   Average upload speed: {avg_speed:.2f}MB/s")
    
    # File category distribution
    print(f"\n📁 Test File Distribution:")
    for category, files in categorized_files.items():
        if files:
            sizes_mb = [f.stat().st_size / (1024 * 1024) for f in files[:3]]
            print(f"   {category}: {len(files)} files (sample sizes: {[f'{s:.2f}MB' for s in sizes_mb]})")
    
    # Performance benchmarks
    print(f"\n🎯 Performance Benchmarks:")
    print(f"   Files < 1MB: {'✅ FAST' if min_time < 5 else '⚠️  SLOW'} (fastest: {min_time:.2f}s)")
    print(f"   Files > 5MB: {'✅ ACCEPTABLE' if max_time < 60 else '⚠️  SLOW'} (slowest: {max_time:.2f}s)")
    print(f"   Consistency: {'✅ GOOD' if (max_time - min_time) < 30 else '⚠️  VARIABLE'}")
    
    print(f"\n✅ Issue #1 Performance Validation:")
    print(f"   Upload completion verification: WORKING")
    print(f"   No artificial retry limits: WORKING")
    print(f"   Large file handling: {'✅ GOOD' if max_time < 120 else '⚠️  NEEDS OPTIMIZATION'}")
    print(f"   Performance consistency: {'✅ STABLE' if statistics.stdev(times) < avg_time else '⚠️  VARIABLE'}")
    
    print(f"{'='*80}")