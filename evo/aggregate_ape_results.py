#!/usr/bin/env python

from evo import main_evaluation as me

if __name__ == '__main__':
    list_of_datasets = [\
                        'MH_01_easy',
                        'MH_02_easy',
                        'MH_03_medium',
                        'mh_04_difficult', # Diff number of left/right imgs...
                        'MH_05_difficult',
                        'V1_01_easy',
                        'V1_02_medium',
                        'V1_03_difficult',
                        'V2_01_easy',
                        'V2_02_medium',
                        'v2_03_difficult' # Diff number of left/right imgs...
                       ]

    list_of_pipelines = ["S", "SP", "SPR"]

    me.aggregate_ape_results(list_of_datasets, list_of_pipelines)
