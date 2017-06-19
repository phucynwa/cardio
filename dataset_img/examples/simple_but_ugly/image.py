# pylint: skip-file
import os
import sys
import numpy as np
from numba import njit
import PIL.Image
import scipy.ndimage
from time import time

sys.path.append("../..")
from dataset import DatasetIndex, Dataset, ImagesBatch, action, inbatch_parallel, any_action_failed

@njit(nogil=True)
def embarassingly_parallel_one(image):
    for i in range(100):
        a = np.sqrt(np.exp(np.log(image + 1)) + 1)
    return a

@njit(nogil=True)
def embarassingly_parallel_all(images):
    for i in range(images.shape[0]):
        new_image = np.sqrt(np.exp(np.log(images[i] + 1)))
    return images


# Example of custom Batch class which defines some actions
class MyImages(ImagesBatch):
    @action
    @inbatch_parallel(init='indices', post='assemble')
    def load(self, ix, src, fmt=None):
        if fmt == 'PIL':
            return PIL.Image.fromarray(src[ix])
        else:
            return src[ix]

    def _add_1(self, x):
        return x + 1

    @action
    @inbatch_parallel(init='indices')
    def epi_one(self, index):
        pos = self.index.get_pos(index)
        self.images[pos] = embarassingly_parallel_one(self.images[pos])

    @action
    @inbatch_parallel(init='images')
    def ep_one(self, image):
        image[:] = embarassingly_parallel_one(image)

    @action
    @inbatch_parallel(init='run_once')
    def ep_all(self):
        embarassingly_parallel_all(self.images)
        return self

    @action
    def transform(self, func):
        #fn = lambda data, factor: scipy.ndimage.zoom(data, factor, order=3)[:S, :S].copy()
        #fn = lambda data: np.diag(np.diag(data))
        return self.apply_transform('images', 'images', func)

    @action
    def print(self):
        print("data len", len(self.data))
        print("images", not self.images is None)
        print("masks", not self.masks is None)
        print("shape:", "No" if self.images is None else self.images.shape)
        #print(np.all(self.images[0] == self[self.indices[0]].images))
        #print(np.all(self.data.images[0] == self[self.indices[0]].images))
        #print(self.images[0])
        return self


if __name__ == "__main__":
    # number of items in the dataset
    K = 10
    S = 12

    # Fill-in dataset with sample data
    def gen_data():
        ix = np.arange(K)
        data = np.random.randint(0, 255, size=K*S*S).reshape(K, S, S).astype('uint8')
        dsindex = DatasetIndex(ix)
        ds = Dataset(index=dsindex, batch_class=MyImages)
        return ds, data


    # Create datasets
    print("Generating...")
    ds_data, data = gen_data()

    #res = ds_data.p.load(data).convert_to_PIL('images').resize((384, 384))
    #res = ds_data.p.load(data).resize((384, 384), method='cv2')
    res = ds_data.p.load(data).epi_one()
    #res = ds_data.p.load(data).transform(embarassingly_parallel_one)

    print("Start...")
    t = time()
    res.run(5, n_epochs=1, prefetch=0)
    print("End", time() - t)
