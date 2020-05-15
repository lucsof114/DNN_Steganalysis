
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.data as td
from torch.utils.tensorboard import SummaryWriter
from dataload import Alaska

def get_dataloaders(dataset_path,b_size,frac_test=0.25):
	alaska_dataset=Alaska(dataset_path)
	N=len(alaska_dataset)
	lengths = [int(N*(1-frac_test)), int(N*frac_test)]
	train_set, dev_set = td.random_split(alaska_dataset, lengths)
	train_loader=td.DataLoader(train_set, batch_size=b_size)
	dev_loader=td.DataLoader(dev_set, batch_size=b_size)
	return train_loader,dev_loader

# train the model from a dataloader and evaluate it every 5 batch  on the dev dataloader
def train(train_loader,dev_loader,model,num_batch,path,lear_rate=1e-4,N_epoch=10):
	tb_writer = SummaryWriter()
	opti= torch.optim.Adam(model.parameters(), lr=lear_rate)
	for epoch in range(N_epoch):
		for batch_index,(X,y_label) in enumerate(train_loader):
			opti.zero_grad()		
			y_pred=model(X)
			#to Device GPU
			loss=F.cross_entropy(y_pred,y_label)
			loss_value=loss.item()
			loss.backward()
			opti.step()
			tb_writer.add_scalar('batch train loss', loss_value, epoch*num_batch+batch_index)
			if batch_index%5==0:
				loss_dev,accuracy_dev=eval_model(model,dev_loader)
				tb_writer.add_scalar('dev loss', loss_dev, epoch*num_batch+batch_index)
				tb_writer.add_scalar('dev accuracy', loss_dev, epoch*num_batch+batch_index)
	torch.save(model.state_dict(), path)
	print('End')
	return 

# evaluate the model on a loader.
def eval_model(model,loader):
    model.eval()
    LOSS=0
    accuracy=0
    for batch_index,(X,y_label) in enumerate(loader):
        y_pred=model(X)
        loss=F.cross_entropy(y_pred,y_label)
        LOSS+=loss.item()
        #accuracy+=(y_label.eq(y_pred.long()).sum()
        accuracy+=y_label.eq(y_pred.long()).sum()
    #accuracy=accuracy/len(loader.dataset)
    #LOSS=LOSS/len(loader.dataset)
    return LOSS,accuracy
    

def test(test_loader,path):
	model = ResNet()
	model.load_state_dict(torch.load(path))
	loss,accuracy=eval_model(model,loader)
	print('Test Loss : '+str(loss))
	print('Test Accuract : '+str(accuracy))