# x3270 Timing Alignment Implementation

This document describes the x3270-compatible timing alignment features implemented in Pure3270 to match x3270's negotiation patterns and timing behavior.

## Overview

The timing alignment implementation provides precise control over TN3270 negotiation timing to match x3270's behavior, ensuring compatibility with servers that expect specific timing patterns during the negotiation process.

## Features

### 1. x3270-Compatible Timing Profiles

Three pre-configured timing profiles are available:

#### Standard Profile (Default)
- **Use Case**: General purpose, balanced timing
- **Initial Delay**: 0.05s
- **Post-TTYPE Delay**: 0.1s
- **Response Timeout**: 3.0s
- **Total Negotiation Timeout**: 15.0s

#### Conservative Profile
- **Use Case**: Slow or unreliable networks
- **Initial Delay**: 0.1s
- **Post-TTYPE Delay**: 0.2s
- **Response Timeout**: 5.0s
- **Total Negotiation Timeout**: 25.0s

#### Aggressive Profile
- **Use Case**: Fast, reliable networks
- **Initial Delay**: 0.02s
- **Post-TTYPE Delay**: 0.05s
- **Response Timeout**: 2.0s
- **Total Negotiation Timeout**: 10.0s

### 2. Step-by-Step Delays

The implementation includes precise delays between negotiation phases:

- **Initial Delay**: Before sending WILL TERMINAL-TYPE
- **Post-TTYPE Delay**: After sending WILL TERMINAL-TYPE
- **Post-DO Delay**: After receiving DO responses
- **Device Type Delay**: Before sending device type information
- **Functions Delay**: Before sending functions information
- **BIND-IMAGE Delay**: Before sending BIND-IMAGE

### 3. Timing Validation and Monitoring

- **Timing Validation**: Ensures operations complete within expected timeframes
- **Step Duration Monitoring**: Tracks duration of each negotiation step
- **Timeout Detection**: Monitors and logs timeout occurrences
- **Metrics Collection**: Comprehensive timing metrics for analysis

### 4. Configurable Timeout Handling

Enhanced timeout handling for different negotiation phases:

- **Negotiation Timeout**: Overall negotiation timeout
- **Device Type Timeout**: Timeout for device type responses
- **Functions Timeout**: Timeout for functions responses
- **Response Timeout**: General response timeout
- **Adaptive Timeouts**: Dynamic timeout adjustment based on network conditions

## Configuration

### Basic Configuration

```python
from pure3270.protocol.tn3270_handler import TN3270Handler

# Create handler with default timing profile
handler = TN3270Handler(None, None)

# Configure timing profile
handler.configure_timing_profile('conservative')

# Enable timing monitoring
handler.enable_timing_monitoring(True)

# Enable step delays
handler.enable_step_delays(True)
```

### Advanced Configuration

```python
# Create handler with specific timing profile
handler = TN3270Handler(None, None)

# Configure aggressive timing for fast networks
handler.configure_timing_profile('aggressive')

# Get current timing profile
current_profile = handler.get_current_timing_profile()
print(f"Current profile: {current_profile}")

# Get timing metrics
metrics = handler.get_timing_metrics()
print(f"Negotiation time: {metrics['total_negotiation_time']:.3f}s")
print(f"Steps completed: {metrics['steps_completed']}")
```

### Direct Negotiator Configuration

```python
from pure3270.protocol.negotiator import Negotiator

negotiator = Negotiator(None, None)

# Configure timing profile
negotiator._configure_x3270_timing_profile('standard')

# Configure timing options
negotiator._configure_timing(
    enable_timing_validation=True,
    enable_step_delays=True,
    enable_timing_monitoring=True,
    timing_metrics_enabled=True
)

# Configure timeouts
negotiator._configure_timeouts(
    negotiation=30.0,
    device_type=10.0,
    functions=10.0,
    response=5.0
)
```

## Timing Metrics

The implementation collects comprehensive timing metrics:

### Available Metrics

- **negotiation_start_time**: When negotiation started
- **negotiation_end_time**: When negotiation completed
- **total_negotiation_time**: Total duration of negotiation
- **steps_completed**: Number of negotiation steps completed
- **timeouts_occurred**: Number of timeouts that occurred
- **delays_applied**: Number of delays applied
- **step_timings**: Dictionary of individual step timings

### Accessing Metrics

```python
# Get metrics after negotiation
metrics = handler.get_timing_metrics()

if metrics:
    print(f"Total negotiation time: {metrics['total_negotiation_time']:.3f}s")
    print(f"Steps completed: {metrics['steps_completed']}")
    print(f"Timeouts: {metrics['timeouts_occurred']}")
    print(f"Delays applied: {metrics['delays_applied']}")

    # Individual step timings
    for step, duration in metrics['step_timings'].items():
        print(f"  {step}: {duration:.3f}s")
```

## Configuration Options

### Timing Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `timing_profile` | str | 'standard' | x3270 timing profile ('standard', 'conservative', 'aggressive') |
| `enable_step_delays` | bool | True | Enable step-by-step delays |
| `enable_timing_monitoring` | bool | True | Enable timing monitoring and logging |
| `timing_metrics_enabled` | bool | True | Enable timing metrics collection |
| `enable_timing_validation` | bool | True | Enable timing validation |

### Timeout Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `negotiation` | float | 30.0 | Overall negotiation timeout |
| `device_type` | float | 10.0 | Device type response timeout |
| `functions` | float | 10.0 | Functions response timeout |
| `response` | float | 5.0 | General response timeout |
| `drain` | float | 2.0 | Writer drain timeout |
| `connection` | float | 15.0 | Connection timeout |
| `telnet_negotiation` | float | 15.0 | Telnet negotiation timeout |
| `tn3270e_negotiation` | float | 20.0 | TN3270E negotiation timeout |

## Usage Examples

### Example 1: Fast Network Configuration

```python
handler = TN3270Handler(None, None)
handler.configure_timing_profile('aggressive')
handler.enable_timing_monitoring(True)
```

### Example 2: Slow Network Configuration

```python
handler = TN3270Handler(None, None)
handler.configure_timing_profile('conservative')
handler.enable_step_delays(True)
```

### Example 3: Custom Timing Configuration

```python
handler = TN3270Handler(None, None)

# Configure custom timing
handler.negotiator._configure_timing(
    timing_profile='standard',
    enable_step_delays=True,
    enable_timing_monitoring=True,
    timing_metrics_enabled=True
)

# Configure custom timeouts
handler.negotiator._configure_timeouts(
    negotiation=25.0,
    device_type=8.0,
    functions=8.0,
    response=4.0
)
```

## Monitoring and Debugging

### Logging

The timing implementation provides detailed logging:

```
[TIMING] Started negotiation timing collection
[TIMING] Applied 0.050s delay for step: initial
[TIMING] Applied 0.100s delay for step: post_ttype
[TIMING] Step initial_ttype completed in 0.025s
[TIMING] Step device_type_send completed in 0.015s
[TIMING] Negotiation completed in 2.847s
[TIMING] Steps completed: 5
[TIMING] Delays applied: 3
[TIMING] Timeouts occurred: 0
```

### Performance Analysis

Use timing metrics to analyze negotiation performance:

```python
import time

start_time = time.time()
# ... perform negotiation ...
end_time = time.time()

metrics = handler.get_timing_metrics()
total_time = end_time - start_time

print(f"Actual negotiation time: {total_time:.3f}s")
print(f"Recorded negotiation time: {metrics['total_negotiation_time']:.3f}s")
print(f"Step breakdown: {metrics['step_timings']}")
```

## Compatibility

- **x3270 Compatibility**: Full compatibility with x3270 timing patterns
- **Backward Compatibility**: Existing code continues to work without changes
- **API Compatibility**: All existing APIs remain unchanged
- **Configuration Compatibility**: New timing options are optional

## Best Practices

1. **Use Standard Profile**: Start with the 'standard' timing profile for most use cases
2. **Monitor Performance**: Enable timing monitoring to identify performance issues
3. **Adjust for Network Conditions**: Use 'conservative' for slow networks, 'aggressive' for fast networks
4. **Enable Metrics**: Keep timing metrics enabled for debugging and optimization
5. **Log Analysis**: Review timing logs to identify bottlenecks in negotiation

## Troubleshooting

### Common Issues

1. **Negotiation Timeouts**: Increase timeout values or use 'conservative' profile
2. **Slow Performance**: Use 'aggressive' profile for faster networks
3. **Intermittent Failures**: Enable step delays and use 'conservative' profile
4. **Debug Timing Issues**: Enable detailed timing logging and metrics collection

### Debug Configuration

```python
# Enable all timing features for debugging
handler = TN3270Handler(None, None)
handler.configure_timing_profile('conservative')
handler.enable_timing_monitoring(True)
handler.enable_step_delays(True)

# Configure detailed logging
import logging
logging.getLogger('pure3270.protocol.negotiator').setLevel(logging.DEBUG)
```

## Implementation Details

### Architecture

The timing implementation consists of:

- **Negotiator Timing**: Core timing logic in `negotiator.py`
- **Handler Integration**: Timing controls in `tn3270_handler.py`
- **Metrics Collection**: Comprehensive timing data collection
- **Profile Management**: Configurable timing profiles
- **Validation System**: Timing constraint validation

### Key Components

- `_x3270_timing_profiles`: Predefined timing profiles
- `_timing_config`: Runtime timing configuration
- `_timing_metrics`: Collected timing data
- `_apply_step_delay()`: Applies delays between steps
- `_record_timing_metric()`: Records step timing data
- `_start_negotiation_timing()`: Initializes timing collection
- `_end_negotiation_timing()`: Finalizes timing collection

This implementation ensures Pure3270 matches x3270's negotiation timing behavior while providing flexibility for different network conditions and use cases.
