# ThingsBoard Gateway BLE Multi-Device Support

## 概述

这个增强版本为 ThingsBoard Gateway 的 BLE 连接器添加了多设备同时连接支持。现在可以在单个 BLE 连接器中同时连接和管理多个 BLE 设备。

## 主要功能

### ✅ 多设备连接
- 支持在单个连接器中同时连接多个 BLE 设备
- 每个设备独立管理连接状态
- 设备间自动错开启动时间，避免连接冲突

### ✅ 设备管理
- 改进的设备配置加载机制
- 增强的设备查找和错误处理
- 优化的设备停止和清理流程

### ✅ 连接稳定性
- 设备启动随机延迟（0-3秒）
- 改进的重连机制
- 优化的连接超时和重试策略

### ✅ 数据转换优化
- 改进的 `BytesBLEUplinkConverter` 数据转换器
- 支持更灵活的数据表达式处理
- 增强的错误处理和日志记录

## 修改的文件

### 1. `device.py`
- **解决单设备连接限制**: 原来每次只能连接成功一个设备，现在支持同时连接多个设备
- **修复设备查找日志问题**: 原来连接成功后仍然打印"无法找到设备"的错误日志，现在修复了设备查找逻辑
- 改进设备启动和停止逻辑
- 增强错误处理和日志记录
- 添加设备启动随机延迟机制

### 2. `bytes_ble_uplink_converter.py`
- 优化数据转换逻辑
- 改进表达式处理机制
- 增强错误处理和异常捕获
- 提升数据转换的稳定性和可靠性

### 3. `ble_connector.py`
- 支持多设备配置加载
- 改进设备管理和连接控制
- 优化连接状态监控

### 4. 配置文件
- `ble.json`: 支持多设备配置
- `tb_gateway.json`: 网关主配置文件

## 使用方法

### 1. 配置设备
在 `ble.json` 配置文件的 `devices` 数组中添加多个设备配置。每个设备需要唯一的名称和MAC地址。

### 2. 启动网关
```bash
cd thingsboard-gateway_3.7.6
python3 tb_gateway.py
```

### 3. 监控连接状态
查看网关日志以监控设备连接状态：
```bash
tail -f logs/tb_gateway.log
```

## 技术特性

### 设备启动延迟
- 每个设备启动时会有 0-3 秒的随机延迟
- 避免多个设备同时尝试连接造成的冲突
- 提高连接成功率

### 独立设备管理
- 每个设备有独立的连接状态
- 设备故障不会影响其他设备
- 支持设备级别的重连机制

### 数据转换增强
- 改进的表达式处理逻辑
- 更好的错误处理和恢复机制
- 增强的数据验证和转换

### 错误处理
- 改进的连接错误处理
- 设备级别的异常隔离
- 详细的错误日志记录

## 兼容性

### 向后兼容
- 完全兼容单设备配置
- 保持原有的数据转换逻辑
- 不影响现有的 RPC 和属性更新功能

### 配置兼容
- 支持现有的设备配置格式
- 无需修改数据转换器
- 保持原有的配置结构

## 故障排除

### 常见问题

1. **设备连接失败**
   - 检查 MAC 地址是否正确
   - 确认设备在范围内且可发现
   - 查看网关日志获取详细错误信息

2. **设备数据不更新**
   - 检查 characteristicUUID 是否正确
   - 确认设备支持指定的特征值
   - 验证数据转换器配置

3. **数据转换错误**
   - 检查数据表达式语法
   - 确认数据格式正确
   - 查看转换器日志获取详细信息

## 版本信息

- **基于版本**: ThingsBoard Gateway 3.7.6
- **修改日期**: 2024年7月
- **支持功能**: 多BLE设备连接、数据转换优化、错误处理增强 
