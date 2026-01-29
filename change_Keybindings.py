import json
import sys
from pathlib import Path

# ==============================================================================
# ============================ 【核心路径配置 - 请修改这里】 ============================
# 兼容 Python 3.12+，路径使用原始字符串避免转义问题
# ==============================================================================
# 默认键位配置文件路径
DEFAULT_KEYBINDINGS_PATH = r"default_Keybindings.json"
# 自定义键位配置文件路径
CUSTOM_KEYBINDINGS_PATH = r"Custom_Keybindings.json"
# 需要替换的目标文件（merged.json）
MERGED_JSON_PATH = r"resource\base\pipeline\merged.json"


# ==============================================================================


def load_keybindings(keybind_path: str) -> dict:
    """
    通用键位加载函数：加载指定路径的键位JSON文件，构建技能名到位置信息的映射
    :param keybind_path: 键位配置文件路径（默认/自定义）
    :return: 映射字典，格式：{技能名: {begin: [...], end: [...], duration: ...}}
    """
    try:
        # 验证文件是否存在
        keybind_file = Path(keybind_path)
        if not keybind_file.exists():
            raise FileNotFoundError(f"文件不存在：{keybind_path}")

        with open(keybind_file, 'r', encoding='utf-8') as f:
            keybind_data = json.load(f)

        # 构建技能名到位置信息的映射
        key_mapping = {}
        for item in keybind_data:
            doc_name = item.get('$doc')
            if doc_name:
                key_mapping[doc_name] = {
                    'begin': item.get('begin', []),
                    'end': item.get('end', []),
                    'duration': item.get('duration', 0)
                }

        print(f"✅ 成功加载 {keybind_file.name}：共 {len(key_mapping)} 个技能配置")
        return key_mapping

    except FileNotFoundError as e:
        print(f"❌ 【错误】找不到键位配置文件：{e}")
        raise
    except json.JSONDecodeError:
        print(f"❌ 【错误】{keybind_path} 不是有效的JSON文件（请检查格式）")
        raise
    except Exception as e:
        print(f"❌ 【错误】加载键位配置时出错：{str(e)}")
        raise


def replace_swipes_data(data: dict or list, key_mapping: dict) -> None:
    """
    递归遍历JSON数据，替换所有swipes数组中的技能位置信息
    兼容Python 3.12+，递归逻辑无版本兼容性问题
    :param data: 要处理的JSON数据（字典或列表）
    :param key_mapping: 技能位置映射字典
    """
    # 如果是列表，遍历每个元素递归处理
    if isinstance(data, list):
        for item in data:
            replace_swipes_data(item, key_mapping)

    # 如果是字典，检查是否包含swipes字段
    elif isinstance(data, dict):
        # 处理当前字典的swipes字段
        if 'swipes' in data and isinstance(data['swipes'], list):
            for swipe_idx, swipe_item in enumerate(data['swipes']):
                if isinstance(swipe_item, dict) and '$doc' in swipe_item:
                    doc_name = swipe_item['$doc']
                    # 如果找到对应的映射，替换位置信息
                    if doc_name in key_mapping:
                        swipe_item['begin'] = key_mapping[doc_name]['begin']
                        swipe_item['end'] = key_mapping[doc_name]['end']
                        swipe_item['duration'] = key_mapping[doc_name]['duration']
                        print(f"  ✔️ 替换技能 [{doc_name}]（索引：{swipe_idx}）")
                    else:
                        print(f"  ⚠️  未找到技能 [{doc_name}] 的配置，跳过替换")

        # 递归处理字典中的其他字段
        for value in data.values():
            replace_swipes_data(value, key_mapping)


def replace_keybindings(keybind_path: str, keybind_type: str) -> None:
    """
    执行键位替换的核心逻辑（无备份逻辑）
    :param keybind_path: 键位配置文件路径
    :param keybind_type: 键位类型（用于提示，如"默认"、"自定义"）
    """
    print(f"\n{'=' * 60}")
    print(f"          开始替换 {keybind_type} 键位（兼容Python 3.12+）")
    print(f"{'=' * 60}")

    try:
        # 1. 加载指定的键位配置
        key_mapping = load_keybindings(keybind_path)

        # 2. 验证目标文件是否存在
        merged_file = Path(MERGED_JSON_PATH)
        if not merged_file.exists():
            print(f"❌ 目标文件不存在：{merged_file}")
            return

        # 3. 读取merged.json
        with open(MERGED_JSON_PATH, 'r', encoding='utf-8') as f:
            merged_data = json.load(f)

        # 4. 替换所有swipes中的技能位置
        print(f"\n🔄 开始替换 {keybind_type} 键位到 {MERGED_JSON_PATH}...")
        replace_swipes_data(merged_data, key_mapping)

        # 5. 保存修改后的文件（直接覆盖，无备份）
        with open(MERGED_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)

        print(f"\n🎉 {keybind_type} 键位替换完成！")
        print(f"📄 修改后的文件：{MERGED_JSON_PATH}")

    except Exception as e:
        print(f"\n❌ 替换 {keybind_type} 键位失败：{str(e)}")


def show_menu() -> None:
    """显示交互菜单，让用户选择替换类型"""
    print("\n" + "=" * 60)
    print("          技能键位替换工具 (兼容 Python 3.12+)")
    print("=" * 60)
    print("📂 配置文件路径：")
    print(f"  默认键位：{DEFAULT_KEYBINDINGS_PATH}")
    print(f"  自定义键位：{CUSTOM_KEYBINDINGS_PATH}")
    print(f"  目标文件：{MERGED_JSON_PATH}")
    print("=" * 60)
    print("请选择操作：")
    print("  0 - 退出程序")
    print("  1 - 替换为【默认键位】")
    print("  2 - 替换为【自定义键位】")
    print("=" * 60)


def main():
    """主函数：处理用户交互和核心逻辑"""
    # 验证Python版本
    python_version = sys.version_info
    if python_version < (3, 12):
        print(f"⚠️  警告：当前Python版本为 {python_version.major}.{python_version.minor}，建议使用3.12及以上版本！")
        print("   程序仍会尝试运行，但可能存在兼容性问题。")
        input("\n按Enter键继续...")

    while True:
        # 显示菜单
        show_menu()

        # 获取用户选择
        try:
            choice = input("请输入数字选择操作（0/1/2）：").strip()

            if choice == '1':
                # 替换默认键位
                replace_keybindings(DEFAULT_KEYBINDINGS_PATH, "默认")
            elif choice == '2':
                # 替换自定义键位
                replace_keybindings(CUSTOM_KEYBINDINGS_PATH, "自定义")
            elif choice == '0':
                # 退出程序
                print("\n👋 程序已退出！")
                break
            else:
                print("\n❌ 输入无效！请输入 0、1 或 2")

        except KeyboardInterrupt:
            # 处理用户按Ctrl+C退出
            print("\n\n👋 用户中断操作，程序退出！")
            break
        except Exception as e:
            print(f"\n❌ 程序出错：{str(e)}")
            continue

        # 操作完成后等待用户确认
        input("\n按Enter键返回菜单...")


if __name__ == "__main__":
    main()
