cd C:\My_Project\AIGC
conda run -n base python AIGuard/clean_dataset.py --dir AIGuard/real
conda run -n base python AIGuard/clean_dataset.py --dir AIGuard/fake
conda run -n base python AIGuard/clean_dataset.py --dir filter_data
conda run -n base python AIGuard/clean_dataset.py --dir FFHQ_four_process --ffhq_exclude
conda run -n base python AIGuard/clean_dataset.py --dir FFHQ_megvii_four_process --ffhq_exclude
conda run -n base python AIGuard/clean_dataset.py --dir FFHQ_ali_process --ffhq_exclude
