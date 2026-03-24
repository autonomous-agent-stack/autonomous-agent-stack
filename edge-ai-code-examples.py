#!/usr/bin/env python3
"""
边缘AI部署代码示例集合

包含五大主流框架的实际代码示例:
- ONNX Runtime
- TensorRT
- TFLite
- OpenVINO
- Core ML (转换代码)

作者: Edge AI Expert
日期: 2025-03-25
"""

import numpy as np
import time
from typing import Tuple, List, Dict, Any, Optional
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# ONNX Runtime 示例
# ============================================================================

class ONNXRuntimeExample:
    """ONNX Runtime 推理示例"""
    
    def __init__(self, model_path: str):
        import onnxruntime as ort
        self.session = ort.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        
        print(f"✅ ONNX Runtime 模型加载成功: {model_path}")
        print(f"   输入形状: {self.session.get_inputs()[0].shape}")
        print(f"   输出形状: {self.session.get_outputs()[0].shape}")
    
    def infer(self, input_data: np.ndarray) -> np.ndarray:
        """执行推理"""
        output = self.session.run([self.output_name], {self.input_name: input_data})
        return output[0]
    
    def benchmark(self, num_runs: int = 100) -> Dict[str, float]:
        """性能测试"""
        # 创建随机输入
        input_shape = self.session.get_inputs()[0].shape
        dummy_input = np.random.rand(*input_shape).astype(np.float32)
        
        # 预热
        for _ in range(10):
            self.infer(dummy_input)
        
        # 测试
        start_time = time.time()
        for _ in range(num_runs):
            self.infer(dummy_input)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / num_runs * 1000
        throughput = 1000 / avg_time
        
        print(f"⚡ 平均推理时间: {avg_time:.2f} ms")
        print(f"📊 吞吐量: {throughput:.2f} FPS")
        
        return {
            'avg_time_ms': avg_time,
            'throughput_fps': throughput
        }
    
    @staticmethod
    def convert_from_pytorch(model: Any, output_path: str, dummy_input: Optional[np.ndarray] = None):
        """从PyTorch转换为ONNX"""
        import torch
        
        if dummy_input is None:
            dummy_input = torch.randn(1, 3, 224, 224)
        
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={
                'input': {0: 'batch_size'},
                'output': {0: 'batch_size'}
            }
        )
        print(f"✅ PyTorch模型已转换为ONNX: {output_path}")


# ============================================================================
# TensorRT 示例
# ============================================================================

class TensorRTExample:
    """TensorRT 推理示例 (需要TensorRT库)"""
    
    def __init__(self, engine_path: str):
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit
            
            self.logger = trt.Logger(trt.Logger.INFO)
            self.runtime = trt.Runtime(self.logger)
            
            # 加载引擎
            with open(engine_path, 'rb') as f:
                self.engine = self.runtime.deserialize_cuda_engine(f.read())
            
            self.context = self.engine.create_execution_context()
            
            print(f"✅ TensorRT引擎加载成功: {engine_path}")
            self._setup_io_buffers()
            
        except ImportError:
            print("⚠️  TensorRT未安装,跳过TensorRT示例")
            self.engine = None
    
    def _setup_io_buffers(self):
        """设置IO缓冲区"""
        import pycuda.driver as cuda
        
        self.inputs = []
        self.outputs = []
        self.bindings = []
        
        for i in range(self.engine.num_io_tensors):
            tensor_name = self.engine.get_tensor_name(i)
            dtype = np.dtype(trt.nptype(self.engine.get_tensor_dtype(tensor_name)))
            shape = self.context.get_tensor_shape(tensor_name)
            size = trt.volume(shape)
            
            # 分配内存
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            
            self.bindings.append(int(device_mem))
            
            if self.engine.get_tensor_mode(tensor_name) == trt.TensorIOMode.INPUT:
                self.inputs.append({
                    'name': tensor_name,
                    'host': host_mem,
                    'device': device_mem,
                    'shape': shape,
                    'dtype': dtype
                })
            else:
                self.outputs.append({
                    'name': tensor_name,
                    'host': host_mem,
                    'device': device_mem,
                    'shape': shape,
                    'dtype': dtype
                })
        
        # 创建CUDA流
        import pycuda.driver as cuda
        self.stream = cuda.Stream()
    
    def infer(self, input_data: np.ndarray) -> List[np.ndarray]:
        """执行推理"""
        if self.engine is None:
            return []
        
        import pycuda.driver as cuda
        
        # 拷贝输入到设备
        for i, input_dict in enumerate(self.inputs):
            np.copyto(input_dict['host'], input_data.ravel())
            cuda.memcpy_htod_async(input_dict['device'], input_dict['host'], self.stream)
        
        # 执行推理
        self.context.execute_async_v3(stream_handle=self.stream.handle)
        
        # 拷贝输出到主机
        for output in self.outputs:
            cuda.memcpy_dtoh_async(output['host'], output['device'], self.stream)
        
        # 同步流
        self.stream.synchronize()
        
        return [output['host'] for output in self.outputs]


# ============================================================================
# TFLite 示例
# ============================================================================

class TFLiteExample:
    """TensorFlow Lite 推理示例"""
    
    def __init__(self, model_path: str):
        import tensorflow as tf
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        print(f"✅ TFLite模型加载成功: {model_path}")
        print(f"   输入形状: {self.input_details[0]['shape']}")
        print(f"   输出形状: {self.output_details[0]['shape']}")
    
    def infer(self, input_data: np.ndarray) -> np.ndarray:
        """执行推理"""
        self.interpreter.set_tensor(
            self.input_details[0]['index'],
            input_data.astype(self.input_details[0]['dtype'])
        )
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        return output
    
    def benchmark(self, num_runs: int = 100) -> Dict[str, float]:
        """性能测试"""
        dummy_input = np.random.rand(*self.input_details[0]['shape']).astype(
            self.input_details[0]['dtype']
        )
        
        # 预热
        for _ in range(10):
            self.infer(dummy_input)
        
        # 测试
        start_time = time.time()
        for _ in range(num_runs):
            self.infer(dummy_input)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / num_runs * 1000
        throughput = 1000 / avg_time
        
        print(f"⚡ 平均推理时间: {avg_time:.2f} ms")
        print(f"📊 吞吐量: {throughput:.2f} FPS")
        
        return {
            'avg_time_ms': avg_time,
            'throughput_fps': throughput
        }
    
    @staticmethod
    def quantize_model(model_path: str, output_path: str, quantization_type: str = 'dynamic'):
        """
        量化TFLite模型
        
        Args:
            model_path: 原始模型路径
            output_path: 量化后模型保存路径
            quantization_type: 'dynamic', 'static', 或 'float16'
        """
        import tensorflow as tf
        
        converter = tf.lite.TFLiteConverter.from_saved_model(model_path)
        
        if quantization_type == 'dynamic':
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        elif quantization_type == 'float16':
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]
        
        elif quantization_type == 'static':
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.representative_dataset = TFLiteExample._representative_dataset()
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            converter.inference_input_type = tf.uint8
            converter.inference_output_type = tf.uint8
        
        tflite_model = converter.convert()
        
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        print(f"✅ 模型量化完成 ({quantization_type}): {output_path}")
    
    @staticmethod
    def _representative_dataset():
        """生成代表性数据集用于静态量化"""
        for _ in range(100):
            data = np.random.rand(1, 224, 224, 3).astype(np.float32)
            yield [data]


# ============================================================================
# OpenVINO 示例
# ============================================================================

class OpenVINOExample:
    """OpenVINO 推理示例"""
    
    def __init__(self, model_xml: str, model_bin: Optional[str] = None, device: str = 'CPU'):
        from openvino.runtime import Core
        
        self.core = Core()
        
        if model_bin:
            self.model = self.core.read_model(model=model_xml, weights=model_bin)
        else:
            self.model = self.core.read_model(model=model_xml)
        
        self.compile_model = self.core.compile_model(
            model=self.model,
            device_name=device,
            config={'PERFORMANCE_HINT': 'LATENCY'}
        )
        
        self.infer_request = self.compile_model.create_infer_request()
        
        self.input_layer = self.compile_model.input(0)
        self.output_layer = self.compile_model.output(0)
        
        print(f"✅ OpenVINO模型加载成功: {model_xml}")
        print(f"   设备: {device}")
        print(f"   输入形状: {self.input_layer.shape}")
        print(f"   输出形状: {self.output_layer.shape}")
    
    def infer(self, input_data: np.ndarray) -> np.ndarray:
        """执行推理"""
        self.infer_request.set_input_tensor(0, input_data)
        self.infer_request.start_async()
        self.infer_request.wait()
        output = self.infer_request.get_output_tensor(0).data
        return output
    
    def benchmark(self, num_runs: int = 100) -> Dict[str, float]:
        """性能测试"""
        dummy_input = np.random.rand(*self.input_layer.shape).astype(np.float32)
        
        # 预热
        for _ in range(10):
            self.infer(dummy_input)
        
        # 测试
        start_time = time.time()
        for _ in range(num_runs):
            self.infer(dummy_input)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / num_runs * 1000
        throughput = 1000 / avg_time
        
        print(f"⚡ 平均推理时间: {avg_time:.2f} ms")
        print(f"📊 吞吐量: {throughput:.2f} FPS")
        
        return {
            'avg_time_ms': avg_time,
            'throughput_fps': throughput
        }
    
    @staticmethod
    def convert_from_onnx(onnx_path: str, output_dir: str = './'):
        """从ONNX转换为OpenVINO格式"""
        from openvino.tools.mo import convert_model
        from openvino.runtime import serialize
        import os
        
        print(f"🔧 正在转换ONNX模型到OpenVINO格式...")
        
        ov_model = convert_model(onnx_path)
        
        base_name = os.path.splitext(os.path.basename(onnx_path))[0]
        xml_path = os.path.join(output_dir, f"{base_name}.xml")
        bin_path = os.path.join(output_dir, f"{base_name}.bin")
        
        serialize(ov_model, xml_path)
        serialize(ov_model, bin_path)
        
        print(f"✅ OpenVINO模型转换完成:")
        print(f"   XML: {xml_path}")
        print(f"   BIN: {bin_path}")
        
        return xml_path, bin_path


# ============================================================================
# Core ML 示例 (仅转换)
# ============================================================================

class CoreMLExample:
    """Core ML 模型转换示例"""
    
    @staticmethod
    def convert_from_pytorch(model: Any, output_path: str, example_input: Optional[np.ndarray] = None):
        """从PyTorch转换为Core ML"""
        import coremltools as ct
        import torch
        
        if example_input is None:
            example_input = torch.rand(1, 3, 224, 224)
        
        # 转换为TorchScript
        traced_model = torch.jit.trace(model, example_input)
        
        # 转换为Core ML
        mlmodel = ct.convert(
            traced_model,
            inputs=[ct.TensorType(shape=example_input.shape)]
        )
        
        # 添加元数据
        mlmodel.short_description = "PyTorch模型转换"
        mlmodel.author = "Edge AI Expert"
        
        # 保存
        mlmodel.save(output_path)
        print(f"✅ Core ML模型转换完成: {output_path}")
    
    @staticmethod
    def quantize_model(model_path: str, output_path: str, nbits: int = 8):
        """量化Core ML模型"""
        import coremltools as ct
        from coremltools.models.neural_network import quantization_utils
        
        model = ct.models.MLModel(model_path)
        
        quantized_model = quantization_utils.quantize_weights(model, nbits=nbits)
        quantized_model.save(output_path)
        
        print(f"✅ Core ML模型量化完成 ({nbits}位): {output_path}")


# ============================================================================
# 性能基准测试
# ============================================================================

class BenchmarkSuite:
    """统一的性能基准测试套件"""
    
    def __init__(self):
        self.results = {}
    
    def run_benchmark(self, inferencer, name: str, num_runs: int = 100):
        """运行基准测试"""
        print(f"\n{'='*50}")
        print(f"📊 测试: {name}")
        print('='*50)
        
        start_time = time.time()
        
        if hasattr(inferencer, 'benchmark'):
            result = inferencer.benchmark(num_runs)
            self.results[name] = result
        else:
            print("⚠️  该推理器不支持benchmark方法")
            result = None
        
        elapsed = time.time() - start_time
        print(f"⏱️  总耗时: {elapsed:.2f} 秒")
        
        return result
    
    def compare_results(self):
        """对比所有测试结果"""
        if not self.results:
            print("没有可对比的结果")
            return
        
        print(f"\n{'='*50}")
        print("📈 性能对比")
        print('='*50)
        print(f"{'框架':<15} {'推理时间(ms)':<15} {'吞吐量(FPS)'}")
        print('-'*50)
        
        for name, result in self.results.items():
            if result and 'avg_time_ms' in result:
                print(f"{name:<15} {result['avg_time_ms']:<15.2f} {result['throughput_fps']:.2f}")
        
        # 找出最佳性能
        if self.results:
            best_time = min(
                (r['avg_time_ms'] for r in self.results.values() if r),
                default=None
            )
            if best_time:
                best_framework = [
                    name for name, result in self.results.items()
                    if result.get('avg_time_ms') == best_time
                ][0]
                print('-'*50)
                print(f"🏆 最佳性能: {best_framework} ({best_time:.2f} ms)")


# ============================================================================
# 实用工具函数
# ============================================================================

class EdgeAIUtils:
    """边缘AI部署实用工具"""
    
    @staticmethod
    def get_model_size(model_path: str) -> float:
        """获取模型文件大小 (MB)"""
        import os
        size_bytes = os.path.getsize(model_path)
        return size_bytes / (1024 * 1024)
    
    @staticmethod
    def compare_model_sizes(model_paths: Dict[str, str]) -> Dict[str, float]:
        """对比多个模型的大小"""
        sizes = {}
        print(f"\n{'='*50}")
        print("📦 模型大小对比")
        print('='*50)
        
        for name, path in model_paths.items():
            try:
                size_mb = EdgeAIUtils.get_model_size(path)
                sizes[name] = size_mb
                print(f"{name:<20} {size_mb:.2f} MB")
            except FileNotFoundError:
                print(f"{name:<20} 文件未找到")
        
        print('='*50)
        return sizes
    
    @staticmethod
    def estimate_memory_usage(model_path: str, batch_size: int = 1) -> float:
        """估算模型内存占用 (MB)"""
        import os
        
        # 模型文件大小
        model_size = os.path.getsize(model_path) / (1024 * 1024)
        
        # 估算运行时内存 (约为模型大小的2-3倍)
        runtime_memory = model_size * 2.5
        
        return runtime_memory
    
    @staticmethod
    def print_system_info():
        """打印系统信息"""
        import platform
        import psutil
        
        print(f"\n{'='*50}")
        print("💻 系统信息")
        print('='*50)
        print(f"操作系统: {platform.system()} {platform.release()}")
        print(f"处理器: {platform.processor()}")
        print(f"核心数: {psutil.cpu_count(logical=False)} (物理)")
        print(f"线程数: {psutil.cpu_count(logical=True)} (逻辑)")
        print(f"内存: {psutil.virtual_memory().total / (1024**3):.2f} GB")
        print('='*50)


# ============================================================================
# 主程序
# ============================================================================

def main():
    """主程序示例"""
    print("🚀 边缘AI部署代码示例")
    print("="*50)
    
    # 打印系统信息
    EdgeAIUtils.print_system_info()
    
    # 示例: 使用ONNX Runtime
    print("\n📝 示例: ONNX Runtime")
    print("-"*50)
    
    # 注意: 需要实际模型文件才能运行
    # onnx_example = ONNXRuntimeExample("model.onnx")
    # result = onnx_example.infer(np.random.rand(1, 3, 224, 224).astype(np.float32))
    
    print("提示: 替换 'model.onnx' 为实际模型路径以运行示例")
    
    # 示例: TFLite量化
    print("\n📝 示例: TFLite模型量化")
    print("-"*50)
    print("TFLiteExample.quantize_model('model_dir', 'model_quant.tflite', 'dynamic')")
    
    # 示例: OpenVINO转换
    print("\n📝 示例: ONNX转OpenVINO")
    print("-"*50)
    print("OpenVINOExample.convert_from_onnx('model.onnx', './')")
    
    print("\n✅ 代码示例加载完成!")
    print("📖 完整文档请参考: edge-ai-deployment-guide.md")


if __name__ == "__main__":
    main()
