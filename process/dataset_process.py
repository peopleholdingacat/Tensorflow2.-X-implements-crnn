import os
import tensorflow as tf
import settings
from read import Dataset


class Preprocess:
    """
    构造传入模型训练的数据集
    """

    def __init__(self):
        self.input_features = settings.input_shape
        self.test_path = settings.test_dataset_path
        self.batch = settings.batch
        self.buffer = settings.burffer
        self.table = tf.lookup.StaticHashTable(
            tf.lookup.TextFileInitializer(
                settings.table_path,
                tf.string,
                tf.lookup.TextFileIndex.WHOLE_LINE,
                tf.int64, tf.lookup.TextFileIndex.LINE_NUMBER
            ), -1)
        train_data = Dataset('train')
        self.train_image_paths, self.train_image_labels = train_data.read()
        val_data = Dataset('val')
        self.val_image_paths, self.val_image_labels = val_data.read()

    def size(self, mode="train"):
        if mode == "train":
            return len(self.train_image_paths)
        else:
            return len(self.val_image_paths)

    def load_and_preprocess_image(self, path, label):
        image = tf.io.read_file(path)
        image = tf.image.decode_jpeg(image, channels=3)
        # 饱和度
        image = tf.image.random_saturation(image, 0, 3)
        # 色调
        image = tf.image.random_hue(image, 0.3)
        # 对比度
        image = tf.image.random_contrast(image, 0.5, 5)
        # 亮度
        image = tf.image.random_brightness(image, max_delta=0.05)
        # resize图片
        resize_image = tf.image.resize(image, self.input_features[:2], preserve_aspect_ratio=True)
        padding_im = tf.image.pad_to_bounding_box(resize_image, 0, 0, self.input_features[0], self.input_features[1])
        return padding_im, label

    def load_and_preprocess_image_predict(self, path):
        image = tf.io.read_file(path)
        image = tf.image.decode_jpeg(image, channels=3)
        # resize图片
        resize_image = tf.image.resize(image, self.input_features[:2], preserve_aspect_ratio=True)
        padding_im = tf.image.pad_to_bounding_box(resize_image, 0, 0, self.input_features[0], self.input_features[1])
        return padding_im

    def decode_label(self, img, label):
        chars = tf.strings.unicode_split(label, "UTF-8")
        tokens = tf.ragged.map_flat_values(self.table.lookup, chars)
        tokens = tokens.to_sparse()
        return img, tokens

    def build(self, mode="train"):
        if mode == "train":
            image_paths, image_labels = self.train_image_paths, self.train_image_labels
        else:
            image_paths, image_labels = self.val_image_paths, self.val_image_labels
        ds = tf.data.Dataset.from_tensor_slices((image_paths, image_labels))
        ds = ds.map(self.load_and_preprocess_image, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        ds = ds.shuffle(buffer_size=self.buffer)
        ds = ds.repeat()
        ds = ds.batch(self.batch)
        ds = ds.map(self.decode_label, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        ds = ds.apply(tf.data.experimental.ignore_errors())
        ds = ds.prefetch(tf.data.experimental.AUTOTUNE)
        return ds

    def build_test(self):
        image_paths = [os.path.join(self.test_path, img) for img in sorted(os.listdir(self.test_path)) if '.jpg' in img]
        image_labels = []
        for file in image_paths:
            with open(file.replace('.jpg', '.txt'), 'r', encoding='utf8') as f:
                label = f.read()
            image_labels.append(label)
        ds = tf.data.Dataset.from_tensor_slices(image_paths)
        ds = ds.map(self.load_and_preprocess_image_predict, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        ds = ds.repeat()
        ds = ds.batch(len(image_paths))
        ds = ds.apply(tf.data.experimental.ignore_errors())
        ds = ds.prefetch(tf.data.experimental.AUTOTUNE)
        return ds, image_labels


if __name__ == '__main__':
    dataset = Preprocess()
    ds = dataset.build()
    print(ds)
