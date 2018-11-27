#!/usr/bin/env python

from evo import main_evaluation as me

if __name__ == '__main__':
    extra_params_to_modify = dict()

    if False:
        test_name = "L2"
        extra_params_to_modify['regularityNormType'] = 0
        extra_params_to_modify['regularityNormParam'] = 0
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.01, 0.02, 0.03, 0.04], False, True, 3, extra_params_to_modify) # 3 means only run SPR

    if False:
        test_name = "Huber_0.5"
        extra_params_to_modify['regularityNormType'] = 1
        extra_params_to_modify['regularityNormParam'] = 1.345
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.01, 0.02, 0.03, 0.04], False, True, 3, extra_params_to_modify) # 3 means only run SPR

    if True:
        test_name = "Tukey_4.685"
        extra_params_to_modify['regularityNormType'] = 2
        extra_params_to_modify['regularityNormParam'] = 4.685
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.01, 0.02, 0.03, 0.04], False, True, 3, extra_params_to_modify) # 3 means only run SPR




#BSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS
    if False:
        test_name = "Mono_Stereo_L2"
        extra_params_to_modify['monoNormType'] = 0
        extra_params_to_modify['stereoNormType'] = 0
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

    if False:
        test_name = "Mono_Stereo_Huber_0.5"
        extra_params_to_modify['monoNormType'] = 1
        extra_params_to_modify['monoNormParam'] = 0.5
        extra_params_to_modify['stereoNormType'] = 1
        extra_params_to_modify['stereoNormParam'] = 0.5
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

    if False:
        test_name = "Mono_Stereo_Huber_1.0"
        extra_params_to_modify['monoNormType'] = 1
        extra_params_to_modify['monoNormParam'] = 1.0
        extra_params_to_modify['stereoNormType'] = 1
        extra_params_to_modify['stereoNormParam'] = 1.0
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

        test_name = "Mono_Stereo_Huber_1.5"
        extra_params_to_modify['monoNormType'] = 1
        extra_params_to_modify['monoNormParam'] = 1.5
        extra_params_to_modify['stereoNormType'] = 1
        extra_params_to_modify['stereoNormParam'] = 1.5
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

        test_name = "Mono_Stereo_Huber_2.0"
        extra_params_to_modify['monoNormType'] = 1
        extra_params_to_modify['monoNormParam'] = 2.0
        extra_params_to_modify['stereoNormType'] = 1
        extra_params_to_modify['stereoNormParam'] = 2.0
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

    if False:
        test_name = "Mono_Stereo_Tukey_1.0"
        extra_params_to_modify['monoNormType'] = 2
        extra_params_to_modify['monoNormParam'] = 1.0
        extra_params_to_modify['stereoNormType'] = 2
        extra_params_to_modify['stereoNormParam'] = 1.0
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

        test_name = "Mono_Stereo_Tukey_1.5"
        extra_params_to_modify['monoNormType'] = 2
        extra_params_to_modify['monoNormParam'] = 1.5
        extra_params_to_modify['stereoNormType'] = 2
        extra_params_to_modify['stereoNormParam'] = 1.5
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

        test_name = "Mono_Stereo_Tukey_2.0"
        extra_params_to_modify['monoNormType'] = 2
        extra_params_to_modify['monoNormParam'] = 2.0
        extra_params_to_modify['stereoNormType'] = 2
        extra_params_to_modify['stereoNormParam'] = 2.0
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

    if False:
        test_name = "Mono_Stereo_Tukey_3.0"
        extra_params_to_modify['monoNormType'] = 2
        extra_params_to_modify['monoNormParam'] = 3.0
        extra_params_to_modify['stereoNormType'] = 2
        extra_params_to_modify['stereoNormParam'] = 3.0
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

    if False:
        test_name = "Mono_Stereo_Tukey_4.0"
        extra_params_to_modify['monoNormType'] = 2
        extra_params_to_modify['monoNormParam'] = 4.0
        extra_params_to_modify['stereoNormType'] = 2
        extra_params_to_modify['stereoNormParam'] = 4.0
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

    if False:
        test_name = "Mono_Stereo_Tukey_4.6851"
        extra_params_to_modify['monoNormType'] = 2
        extra_params_to_modify['monoNormParam'] = 4.6851
        extra_params_to_modify['stereoNormType'] = 2
        extra_params_to_modify['stereoNormParam'] = 4.6851
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

    if False:
        test_name = "Mono_Stereo_Tukey_5.0"
        extra_params_to_modify['monoNormType'] = 2
        extra_params_to_modify['monoNormParam'] = 5.0
        extra_params_to_modify['stereoNormType'] = 2
        extra_params_to_modify['stereoNormParam'] = 5.0
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR

        test_name = "Mono_Stereo_Tukey_6.0"
        extra_params_to_modify['monoNormType'] = 2
        extra_params_to_modify['monoNormParam'] = 6.0
        extra_params_to_modify['stereoNormType'] = 2
        extra_params_to_modify['stereoNormParam'] = 6.0
        params_to_test = ["monoNoiseSigma", "stereoNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [[0.8, 0.8],
                                                              [1.0, 1.0],
                                                              [1.2, 1.2],
                                                              [1.4, 1.4],
                                                              [1.6, 1.6],
                                                              [1.8, 1.8]],
                                  True, True, 6, extra_params_to_modify) # 6 means run SP and SPR
        ################## Smart Noise #######################################################

    if False:
        test_name = "Smart"
        params_to_test = ["smartNoiseSigma"]
        me.regression_test_simple(test_name, params_to_test, [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5,
                                                              2.75, 3.0, 3.25, 3.5],
                                  True, True, 0, extra_params_to_modify) # 0 means run S, SP and SPR


        ################## REG NORM #######################################################

    if False:
        test_name = "Tukey_4.0"
        extra_params_to_modify['regularityNormType'] = 2
        extra_params_to_modify['regularityNormParam'] = 4.0
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Tukey_4.3"
        extra_params_to_modify['regularityNormType'] = 2
        extra_params_to_modify['regularityNormParam'] = 4.3
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Tukey_4.6851"
        extra_params_to_modify['regularityNormType'] = 2
        extra_params_to_modify['regularityNormParam'] = 4.6851
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Tukey_5.0"
        extra_params_to_modify['regularityNormType'] = 2
        extra_params_to_modify['regularityNormParam'] = 5.0
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Tukey_1.0"
        extra_params_to_modify['regularityNormType'] = 2
        extra_params_to_modify['regularityNormParam'] = 1.0
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Tukey_2.0"
        extra_params_to_modify['regularityNormType'] = 2
        extra_params_to_modify['regularityNormParam'] = 2.0
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Tukey_3.0"
        extra_params_to_modify['regularityNormType'] = 2
        extra_params_to_modify['regularityNormParam'] = 3.0
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Tukey_3.5"
        extra_params_to_modify['regularityNormType'] = 2
        extra_params_to_modify['regularityNormParam'] = 3.5
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR


    if False:
        test_name = "L2"
        extra_params_to_modify['regularityNormType'] = 0
        extra_params_to_modify['regularityNormParam'] = 0
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

    if False:
        test_name = "Huber_0.5"
        extra_params_to_modify['regularityNormType'] = 1
        extra_params_to_modify['regularityNormParam'] = 0.5
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Huber_0.6"
        extra_params_to_modify['regularityNormType'] = 1
        extra_params_to_modify['regularityNormParam'] = 0.6
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

    if False:
        test_name = "Huber_0.7"
        extra_params_to_modify['regularityNormType'] = 1
        extra_params_to_modify['regularityNormParam'] = 0.7
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Huber_0.8"
        extra_params_to_modify['regularityNormType'] = 1
        extra_params_to_modify['regularityNormParam'] = 0.8
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Huber_0.9"
        extra_params_to_modify['regularityNormType'] = 1
        extra_params_to_modify['regularityNormParam'] = 0.9
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Huber_1.0"
        extra_params_to_modify['regularityNormType'] = 1
        extra_params_to_modify['regularityNormParam'] = 1.0
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

        test_name = "Huber_1.1"
        extra_params_to_modify['regularityNormType'] = 1
        extra_params_to_modify['regularityNormParam'] = 1.1
        me.regression_test_simple(test_name, ["regularityNoiseSigma"], [0.02, 0.03, 0.04, 0.05], True, True, 3, extra_params_to_modify) # 3 means only run SPR

    #me.regression_test_simple("stereoNoiseSigma", [1.5, 1.6, 1.7])
    #me.regression_test_simple("monoNoiseSigma", [1.5, 1.6, 1.7])
