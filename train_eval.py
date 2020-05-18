
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.data as td
import random
import sys
from tqdm import tqdm

#from torch.utils.tensorboard import SummaryWriter
from tensorboardX import SummaryWriter
from dataload import Alaska
from models import *
from utils import get_available_devices, AverageMeter
from args import *


params = load_params()

def get_dataloaders(alaska_dataset):
    b_size = params["batch_size"]
    frac_test = params["data_split_frac"]
    N=len(alaska_dataset)
    print("Training set :{}".format(int(N*(1-frac_test))))
    print("Dev set:{}".format(int(N*frac_test)))
    lengths = [int(N*(1-frac_test)), int(N*frac_test)]
    train_set, dev_set = td.random_split(alaska_dataset, lengths)
    train_loader=td.DataLoader(train_set, batch_size=b_size, shuffle = True, drop_last = True)
    if params["overfitting"] =="True":
        print("Overfitting mode")
        dev_loader=td.DataLoader(train_set, batch_size=b_size, drop_last = True)
    else:
        print("Training mode")
        dev_loader=td.DataLoader(dev_set, batch_size=b_size, drop_last = True)

    return train_loader,dev_loader

def prepbatch(X, y) : 
    X = X.view(-1, 3, params["image_size"],  params["image_size"])
    y = y.view(-1)
    return X, y

def init_seed() :
    random.seed(params["seed"])
    torch.manual_seed(params["seed"])
    torch.cuda.manual_seed_all(params["seed"])

        
# train the model from a dataloader and evaluate it every 5 batch  on the dev dataloader
def train(train_loader,dev_loader,model, device):
    N_epoch = params["num_epochs"]
    lear_rate = params["learning_rate"]
    images_seen = 0
    tb_writer = SummaryWriter("save/"+params["name"]+"/")
    opti= torch.optim.Adam(model.parameters(), lr=lear_rate)
    avg = AverageMeter()
    time2eval = params["evaluate_every"]
    for epoch in range(N_epoch):
        print("Starting Epoch: ", epoch)
        avg.reset()
        with torch.enable_grad(), tqdm(total=len(train_loader.dataset)*params["size_factor"]) as pbar:
            for batch_index,(X,y_label) in enumerate(train_loader):
                X = X.to(device)
                y_label = y_label.to(device)
                X, y_label = prepbatch(X, y_label)
                batch_size = X.shape[0]
                #print(y_label)
                opti.zero_grad()
                y_pred=model(X)

                loss=F.cross_entropy(y_pred,y_label)           
                loss_value=loss.item()
                pbar.update(batch_size)
                avg.update(loss_value,batch_size)
                pbar.set_postfix(loss =avg.avg, epoch= epoch)
                #print('Batch loss: {}'.format(loss))
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), params["grad_max_norm"])
                opti.step()  
                tb_writer.add_scalar('batch train loss', loss_value , images_seen)
                images_seen += batch_size
                time2eval -= batch_size
                if time2eval <= 0:
                    time2eval = params["evaluate_every"]
                    loss_dev,accuracy_dev=eval_model(model,dev_loader, device)
                    print('Dev Loss: {}'.format(loss_dev))
                    print('Accuracy: {}'.format(accuracy_dev))
                    tb_writer.add_scalar('dev loss', loss_dev, images_seen)
                    tb_writer.add_scalar('dev accuracy', accuracy_dev, images_seen)
                #torch.save(model.state_dict(), path) 

# evaluate the model on a loader.
def eval_model(model,loader, device):
    model.eval()
    LOSS=0
    accuracy=0
    num = 0
    avg = AverageMeter()
    print("")
    with torch.no_grad(),tqdm(total=len(loader.dataset)*params["size_factor"],position=0, leave=True) as pbar2:
        for batch_index,(X,y_label) in enumerate(loader):

            X = X.to(device)
            y_label = y_label.to(device)

            X, y_label = prepbatch(X, y_label)
            num += X.shape[0]
            y_pred=model(X)
            loss=F.cross_entropy(y_pred,y_label)
            LOSS+=loss.item()
            avg.update(LOSS, X.shape[0])
            pbar2.update(X.shape[0])
            pbar2.set_postfix(loss =avg.avg)
            _, pred_classes = y_pred.max(dim = 1)
            accuracy+=y_label.eq(pred_classes.long()).sum()
            # print("Eval successful")
        #print(accuracy)
    accuracy=accuracy.item()/num
    LOSS=LOSS/len(loader)
    print('Num : {}'.format(num))
    model.train()
    return LOSS,accuracy
    
def overfit_train(frac_test=0.05):
    device, gpu_ids = get_available_devices()
    print(device)
    AlaskaDataset=Alaska("./data","pairs",1, "multi")
    N=len(AlaskaDataset)
    lengths = [int(N*(frac_test)),int(N*(1-frac_test))]	
    train_set,other= td.random_split(AlaskaDataset, lengths)
    other=0
    train_loader=td.DataLoader(train_set, batch_size=2)
    model = SRNET()  
    model = model.to(device)
    train(train_loader,train_loader,model, device)

def test(test_loader,Model,path):
	model = Model
	model.load_state_dict(torch.load(path))
	loss,accuracy=eval_model(model,test_loader)
	print('Test Loss : '+str(loss))
	print('Test Accuract : '+str(accuracy))

if __name__ == '__main__':
    params = load_params()
    save_params(params)
    params['name'] = sys.argv[1]
    device, gpu_ids = get_available_devices()
    print(device)
    AlaskaDataset= Alaska()
    #model = Net(4)
    #model =SmallNet()
    #model = SRNET()
    model = ResNet(4)
    model = model.to(device)
    model.train()

    train_loader,dev_loader=get_dataloaders(AlaskaDataset)

    train(train_loader,dev_loader,model, device)
