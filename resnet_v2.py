'''
A pratice to build ResNet unit, in order to stack these unit to build Residual Network

Using CIFAR10 as testing dataset
'''
import keras
from keras.datasets import cifar10
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential, Model
from keras.layers import Dense, Conv2D, MaxPooling2D, GlobalAveragePooling2D, BatchNormalization, Activation, Add, Input
from keras import optimizers, regularizers
from keras.callbacks import LearningRateScheduler

num_classes        = 10
batch_size         = 128
epochs             = 200
iterations         = (50000// batch_size) +1
weight_decay       = 1e-4

def scheduler(epoch):
    if epoch < 80:
        return 1e-1
    if epoch < 150:
        return 1e-2
    return 1e-3

def color_preprocessing(x_train,x_test):
    x_train = x_train.astype('float32')
    x_test = x_test.astype('float32')
    mean = [125.307, 122.95, 113.865]
    std  = [62.9932, 62.0887, 66.7048]

    for i in range(3):
        x_train[:,:,:,i] = (x_train[:,:,:,i] - mean[i]) / std[i]
        x_test[:,:,:,i] = (x_test[:,:,:,i] - mean[i]) / std[i]
    return x_train, x_test

def conv1x1(img, filters, stride=(1,1)):
    x = BatchNormalization(momentum=0.9, epsilon=1e-5)(img)
    x = Activation('relu')(x)
    x = Conv2D(filters, kernel_size=(1,1), strides=stride, padding='same',
                use_bias=False, kernel_initializer='he_normal',
                kernel_regularizer=regularizers.l2(weight_decay))(x)
    return x

def conv3x3(img, filters):
    x = BatchNormalization(momentum=0.9, epsilon=1e-5)(img)
    x = Activation('relu')(x)
    x = Conv2D(filters, kernel_size=(3,3), use_bias=False, padding='same',
                kernel_initializer='he_normal',
                kernel_regularizer=regularizers.l2(weight_decay))(x)
    return x

def identity(img, filters):
    shortcut = img

    x = conv3x3(img, filters)
    x = conv3x3(x, filters)
    x = Add()( [x, shortcut])

    return x

def projection_block(img, filters, stride=(2,2)):
    x = BatchNormalization(momentum=0.9, epsilon=1e-5)(img)
    x = Activation('relu')(x)

    shortcut = x

    x = Conv2D(filters, kernel_size=(3,3), strides=stride, padding='same',
                use_bias=False, kernel_initializer='he_normal',
                kernel_regularizer=regularizers.l2(weight_decay))(x)
    x = conv3x3(x, filters)

    shortcut = Conv2D(filters, kernel_size=(1,1), strides=stride, padding='same',
                      use_bias=False, kernel_initializer='he_normal',
                      kernel_regularizer=regularizers.l2(weight_decay))(shortcut)
    x = Add()( [x, shortcut])

    return x

def bottleneck(img, filters, stride=(2,2)):
    out_filter = 4 * filters

    x = BatchNormalization(momentum=0.9, epsilon=1e-5)(img)
    x = Activation('relu')(x)

    shortcut = x

    x = Conv2D(filters, kernel_size=(1,1), strides=stride, padding='same',
                use_bias=False, kernel_initializer='he_normal',
                kernel_regularizer=regularizers.l2(weight_decay))(x)
    x = conv3x3(x, filters)
    x = conv1x1(x, out_filter)

    shortcut = conv1x1(shortcut, out_filter, stride=stride)

    x = Add()( [x, shortcut])

    return x

def resnet_v2(img, filters, stacks):
    x = Conv2D(filters[0], kernel_size=(3,3), strides=(1,1), padding='same',
                use_bias=False, kernel_initializer='he_normal',
                kernel_regularizer=regularizers.l2(weight_decay))(img)

    for i in range(stacks):
        x = identity(x, filters[0])

    x = projection_block(x, filters[1])
    for i in range(1, stacks):
        x = identity(x, filters[1])

    x = projection_block(x, filters[2])
    for i in range(1, stacks):
        x = identity(x, filters[2])

    x = BatchNormalization(momentum=0.9, epsilon=1e-5)(x)
    x = Activation('relu')(x)
    x = GlobalAveragePooling2D()(x)
    x = Dense(num_classes,activation='softmax',
                kernel_initializer='he_normal',
                kernel_regularizer=regularizers.l2(weight_decay))(x)
    return x

if __name__ == '__main__':
    filters = [16,32,64]
    stacks  = 9

    (x_train, y_train), (x_test, y_test) = cifar10.load_data()

    y_train = keras.utils.to_categorical(y_train, num_classes)
    y_test = keras.utils.to_categorical(y_test, num_classes)
    x_train, x_test = color_preprocessing(x_train, x_test)

    # construct model
    img_input   = Input(shape=(32,32,3))
    output      = resnet_v2(img_input, filters=filters, stacks=stacks)
    resnet      = Model(img_input, output)

    resnet.summary()

    # set optimizer
    sgd = optimizers.SGD(lr=.1, momentum=0.9, nesterov=True)
    resnet.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])

    # set callback
    cbks = [LearningRateScheduler(scheduler)]

    # set data augmentation
    print("== Using real-time data augmentation, start training... ==")
    datagen = ImageDataGenerator(horizontal_flip=True,
                                 width_shift_range=0.125,
                                 height_shift_range=0.125,
                                 fill_mode='constant',cval=0.)
    datagen.fit(x_train)

    # start training
    resnet.fit_generator(datagen.flow(x_train, y_train,batch_size=batch_size),
                         steps_per_epoch=iterations,
                         epochs=epochs,
                         callbacks=cbks,
                         validation_data=(x_test, y_test))

    scores = resnet.evaluate(x_test, y_test, batch_size=256)
    print('Accy: %06.5f' % scores[1])
