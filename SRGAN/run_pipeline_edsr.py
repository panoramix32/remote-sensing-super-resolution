import os
from data import CATESR
from model.edsr import edsr
from train import EdsrTrainer, SrganTrainer
from model.srgan import discriminator


if __name__ == "__main__":

    depth = 16    # Number of residual blocks
    scale = 4    # Super-resolution factor

    # Location of model weights
    weights_dir = 'weights/edsr'
    weights_file = os.path.join(weights_dir, 'weights.h5')

    os.makedirs(weights_dir, exist_ok=True)

    catesr_train = CATESR(subset='train', images_dir='/home/ec2-user/gans/data/images_rgb',
                          caches_dir='/home/ec2-user/gans/data/caches_rgb')
    catesr_valid = CATESR(subset='valid', images_dir='/home/ec2-user/gans/data/images_rgb',
                          caches_dir='/home/ec2-user/gans/data/caches_rgb')


    train_ds = catesr_train.dataset(batch_size=1, random_transform=True, shuffle_buffer_size=500)
    valid_ds = catesr_valid.dataset(batch_size=1, random_transform=False, repeat_count=1)

    generator_model = edsr(scale=scale, num_res_blocks=depth)
    generator_model.load_weights(os.path.join(weights_dir, 'pretrained_weights-edsr-16-x4-fine-tuned.h5'))

    trainer = EdsrTrainer(model=generator_model, checkpoint_dir=f'.ckpt/edsr-{depth}-x{scale}')

    # Train EDSR model for 300,000 steps Save a checkpoint only if evaluation PSNR has improved.
    trainer.train(train_ds,
                  valid_ds.take(20),
                  steps=300000,
                  evaluate_every=1000,
                  save_best_only=True)

    # Restore from checkpoint with highest PSNR
    trainer.restore()

    # Evaluate model on full validation set
    psnrv = trainer.evaluate(valid_ds)
    print(f'PSNR = {psnrv.numpy():3f}')

    # Save weights to separate location
    trainer.model.save_weights(weights_file)

    # Create EDSR generator and init with pre-trained weights
    generator = edsr(scale=4, num_res_blocks=16)
    generator.load_weights('weights/edsr/weights.h5')

    # Fine-tune EDSR model via SRGAN training.
    gan_trainer = SrganTrainer(generator=generator, discriminator=discriminator())
    gan_trainer.train(train_ds, steps=50000)

    new_weights_file = os.path.join(weights_dir, 'weights_fine_tuned_50000_steps.h5')
    generator.save_weights(new_weights_file)
