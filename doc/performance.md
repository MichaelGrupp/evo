# Performance

Although Python's adavantages are definitely more in the area of flexibility than in in raw performance, evo still tries to work as efficient as possible to keep annoying delays small. This is achieved with efficient algorithms, heavy use of libs like numpy or pandas for handling large data, lazy evaluation patterns, list/dict comprehensions over plain loops etc. - all things that you don't care about as a user but make it faster to work with.

Even if you don't really need all features, you can consider it also as a replacement for simpler scripts.
Here's a comparison with the Python-based evaluation tools from the popular TUM RGB-D dataset ([source](https://vision.in.tum.de/data/datasets/rgbd-dataset/tools), [extended version](https://github.com/raulmur/evaluate_ate_scale)) using a rather large ground truth trajectory with 20957 poses ([data](../test/data)). Small numerical differences are expected.

**Absolute translation error (same settings)**

```
$ time ./evaluate_ate.py fr2_desk_groundtruth.txt fr2_desk_ORB.txt --verbose

compared_pose_pairs 2223 pairs
absolute_translational_error.rmse 0.008144 m
absolute_translational_error.mean 0.007514 m
absolute_translational_error.median 0.007432 m
absolute_translational_error.std 0.003140 m
absolute_translational_error.min 0.000332 m
absolute_translational_error.max 0.024329 m

real	0m16.753s
user	0m16.824s
sys	0m0.204s
```

---

```
$ time evo_ape tum fr2_desk_groundtruth.txt fr2_desk_ORB.txt --align

APE w.r.t. translation part (m)
(with SE(3) Umeyama alignment)

       max	0.024300
      mean	0.007492
    median	0.007415
       min	0.000350
      rmse	0.008119
       sse	0.143305
       std	0.003129


real	0m0.735s
user	0m0.764s
sys	0m0.272s
```

The difference is so obvious that further profiling is not really needed. But it shows that `evaluate_ate.py` spends most of its time associating the timestamps of the two trajectories, which is implemented more efficient in evo's sync module.


## Plotting

...makes everything a bit slower unfortunately, mainly because loading matplotlib consumes up to a few seconds. If you want to do a large number of plots, consider coding a custom script that loads matplotlib only once.
