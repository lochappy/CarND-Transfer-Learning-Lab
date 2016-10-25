from keras.applications.resnet50 import ResNet50
from keras.applications.inception_v3 import InceptionV3
from keras.applications.vgg16 import VGG16
from keras.layers import Dense, Flatten, Input
from sklearn.model_selection import train_test_split
from keras.models import Model
from keras.datasets import cifar10
from skimage.transform import resize
import numpy as np
import pickle
import tensorflow as tf

flags = tf.app.flags
FLAGS = flags.FLAGS

flags.DEFINE_string('dataset', 'cifar10', "Make bottleneck features this for dataset, one of 'cifar10', or 'traffic'")
flags.DEFINE_string('model_type', 'resnet', "The model to bottleneck, one of 'vgg', 'inception', or 'resnet'")
flags.DEFINE_integer('batch_size', 10, 'The batch size for the generator')


nb_classes = 10
batch_size = FLAGS.batch_size

def gen(data, labels, batch_size, size=(224, 224)):
    def _f():
        start = 0
        end = start + batch_size
        n = data.shape[0]
        while True:
            X_batch_old, y_batch = data[start:end], labels[start:end]
            X_batch = []
            for i in range(X_batch_old.shape[0]):
                img = resize(X_batch_old[i, ...], size)
                X_batch.append(img)

            X_batch = np.array(X_batch)
            start += batch_size
            end += batch_size
            if start >= n:
                start = 0
                end = batch_size

            yield (X_batch, y_batch)

    return _f


def create_model():
    input_tensor = Input(shape=(224, 224, 3))
    if FLAGS.model_type == 'vgg':
        model = VGG16(input_tensor=input_tensor, include_top=False, weights='imagenet')
    elif FLAGS.model_type == 'inception':
        model = InceptionV3(input_tensor=input_tensor, include_top=False, weights='imagenet')
    else:
        model = ResNet50(input_tensor=input_tensor, include_top=False, weights='imagenet')
    model.compile(optimizer='sgd', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

    return model

def main(_):
    (X_train, y_train), (_, _) = cifar10.load_data()
    X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.2, random_state=0)

    X_train = X_train.astype('float32')
    X_val = X_val.astype('float32')
    X_train /= 255
    X_val /= 255

    model = create_model()
    train_gen = gen(X_train, y_train, batch_size)
    val_gen = gen(X_val, y_val, batch_size)

    print('Bottleneck training')
    bottleneck_features_train = model.predict_generator(train_gen(), X_train.shape[0])
    print('Bottleneck validation')
    bottleneck_features_validation = model.predict_generator(val_gen(), X_val.shape[0])

    train_data = {'features': bottleneck_features_train, 'labels': y_train}
    validation_data = {'features': bottleneck_features_validation, 'labels': y_val}
    train_output_file = "{}_{}_{}.p".format(FLAGS.model_type, FLAGS.dataset, 'bottleneck_features_train')
    validation_output_file = "{}_{}_{}.p".format(FLAGS.model_type, FLAGS.dataset, 'bottleneck_features_validation')
    pickle.dump(train_data, open(train_output_file, 'wb'))
    pickle.dump(validation_data, open(validation_output_file, 'wb'))

if __name__ == '__main__':
    tf.app.run()
