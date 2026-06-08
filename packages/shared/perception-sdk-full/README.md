# perception-sdk-full

`perception-sdk-full` 是 Munk AI 当前默认的 `full` perception provider 实现包。

它的职责是：

- 提供 `munk.perception` API 所需的具体 provider 实现
- 自己持有并解析 OCR / icon detection 的运行时资源
- 自己持有全部 perception 内部算法与图像处理逻辑
- 通过 entry point `munk.perception.providers` 注册 `full` provider

主仓只负责安装和调用这个 provider，不再负责维护 perception 模型目录或模型文件名。
主仓也不再持有 `annotate`、`ui_tree`、`screen_graph_builder`、`geometry` 等 perception 内部实现。

## 目录边界

当前目录结构的 ownership 如下：

```text
packages/shared/perception-sdk-full/
  README.md
  pyproject.toml
  icon_detect/                             # 训练/导出相关产物，不随 wheel 分发
    model.pt
    model.yaml
    train_args.yaml
    onnx/
      icon_detect.onnx                     # 维护者侧明文源模型
  src/
    munk_perception_full/
      assets.py                            # 资源解析与诊断入口
      provider.py                          # full provider factory
      resources/                           # 运行时资源根目录，会随 wheel 分发
        models/
          detect/
            detect.onnx
        vision-core/
          vision_det_a.onnx
          vision_det_a.json
          vision_rec_a.onnx
          vision_rec_a.yml
          vision_rec_a.keys.txt
          vision_cls_a.onnx
```

## 资源 ownership

运行时资源统一放在 `src/munk_perception_full/resources/`：

- 这里的文件是 `full` provider 运行时直接消费的资产
- 这些文件会通过 `pyproject.toml` 中的 package data 配置随 wheel 一起打包
- 默认情况下，`assets.py` 只从这里解析资源
- icon detect 模型当前以 `resources/models/detect/detect.onnx` 形式分发

模型准备辅助逻辑位于 `perception-sdk-full/build_helpers.py`：

- 构建时会把远端 `detect.onnx` 下载到 `src/munk_perception_full/resources/models/detect/`
- 下载得到的明文模型属于运行时 contract，会随 wheel / standalone runtime 分发

主仓根目录不应再保留 perception 运行时资源副本：

- 不再依赖维护者本地 `icon_detect/onnx/icon_detect.onnx`
- 不再保留根目录 `vision-core/` 之外的 OCR 运行时副本
- 如果出现新的主仓副本，应视为 ownership 回退并尽快清理

## 解析规则

`src/munk_perception_full/assets.py` 的当前规则是：

- 若 `options["resource_root"]` 存在，则优先读取该目录
- 否则若环境变量 `MUNK_PERCEPTION_RESOURCE_ROOT` 存在，则读取该目录
- 否则默认读取包内 `src/munk_perception_full/resources/`

这意味着：

- 开发态和 wheel 态的默认资源 owner 都是 `perception-sdk-full`
- 只有显式 override 时，provider 才会使用外部资源目录
- provider 不再隐式回退到主仓根目录查找模型

## 修改资源时的规则

如果你新增、替换或删除运行时模型文件，请同时检查以下位置：

- `src/munk_perception_full/resources/`
- `src/munk_perception_full/assets.py`
- `pyproject.toml`

如果改动会影响 OCR keys 生成或资源命名，也需要确认：

- `assets.py` 中 `vision_rec_a.keys.txt` 的解析逻辑
- `provider.py` / `engine.py` / `ocr.py` 是否仍与资源 contract 一致

## 打包说明

`pyproject.toml` 当前声明：

```toml
[tool.setuptools.package-data]
munk_perception_full = ["resources/**/*"]
```

这表示只有 `munk_perception_full/resources/` 会作为包资源随 wheel 分发。

因此：

- 运行时必须依赖的资源，必须放进 `resources/`
- 训练材料、实验文件、导出脚本产物，不应放进 `resources/`
- OCR 原始官方模型目录应放在仓库根的 `models/`，不要放回 `resources/`
- release wheel / standalone runtime 应携带 `detect.onnx`

## 第一批 Cython 编译边界

当前 `full` provider 的第一批核心实现已按 `Cython` 编译接入构建链：

- `engine.py`
- `ocr.py`
- `icon.py`
- `fusion.py`
- `geometry.py`

边界约束：

- 显式开启 Cython 构建时，正式 wheel 只分发这些模块的编译产物，不再分发同名 `.py`
- 默认情况下不构建这些模块的 `.so`，而是保留并分发同名 `.py`
- 入口与装配层继续保留 Python 形态：
  - `__init__.py`
  - `provider.py`
  - `assets.py`
  - `annotate.py`
  - `image_io.py`
  - `pipeline.py`
- 这样可以同时保持：
  - entry point `munk.perception.providers`
  - package data 资源分发
  - provider 资源定位与 diagnostics
  - 主仓对 `full` provider 的现有导入/装配兼容

开发和发行规则：

- 发行态 wheel 仍通过 `python -m build` 构建，但默认不会构建 `.so`
- 开发态继续通过 `python3 scripts/bootstrap_standalone_dev.py` 做 editable 安装，默认同样不构建 `.so`
- 只有在环境变量 `MUNK_ENABLE_CYTHON=1` 或顶层装配脚本显式传入 `--enable-cython` 时，才会构建这些编译扩展
- `python3 scripts/bootstrap_standalone_dev.py --force` 与 `python3 scripts/assemble_standalone_runtime.py --force` 都会额外清理源码树中残留的 `.so/.pyd`
- 当 `perception-sdk-full` 的源码或 `setup.py` 变更时，bootstrap / assemble 脚本的源码指纹会触发重新安装或重新构建

## 开发建议

- 运行时资产优先保持最小集合，不要把无关训练中间文件塞进 `resources/`
- 如果后续引入新的 provider 变体，资源目录和 entry point 应继续按 provider 自治，不要回流到主仓
- 若需要本地调试外部资源目录，优先使用 `MUNK_PERCEPTION_RESOURCE_ROOT` 或 runtime `options["resource_root"]`，不要恢复主仓路径 hack
