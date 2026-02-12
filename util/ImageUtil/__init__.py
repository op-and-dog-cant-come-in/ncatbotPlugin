from PIL import Image
from PIL.Image import Resampling


def resize_image(input_path, output_path, max_height=400):
    """
    将本地图片压缩为指定大小，保持原有比例。

    :param input_path: 原始图片路径
    :param output_path: 输出图片路径
    :param max_height: 最大高度，默认为 400
    """
    # 打开原始图片
    with Image.open(input_path) as img:
        # 获取原始图片的宽高
        original_width, original_height = img.size

        # 如果图片高度不超过 max_height，则直接保存
        if original_height <= max_height:
            resized_img = img.resize(size=(original_width, original_height), resample=Resampling.LANCZOS)
            resized_img.save(output_path)
        else:
            # 按比例缩放图片，使高度为 max_height
            ratio = max_height / original_height
            new_width = int(original_width * ratio)
            # 调整图片尺寸
            resized_img = img.resize(size=(new_width, max_height), resample=Resampling.LANCZOS)
            # 保存调整后的图片
            resized_img.save(output_path)
    return output_path


if __name__ == '__main__':
    # 示例调用
    input_image = r"D:\github\ncatbotPlugin\cover\1254394.jpg"  # 输入图片路径
    output_image = "resized_example.jpg"  # 输出图片路径
    resize_image(input_image, output_image)
