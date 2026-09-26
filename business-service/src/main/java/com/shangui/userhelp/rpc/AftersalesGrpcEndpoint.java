package com.shangui.userhelp.rpc;

import com.shangui.userhelp.aftersales.domain.ReturnInfo;
import com.shangui.userhelp.aftersales.domain.WarrantyInfo;
import com.shangui.userhelp.aftersales.service.AftersalesService;
import io.grpc.stub.StreamObserver;
import net.devh.boot.grpc.server.service.GrpcService;

@GrpcService
public class AftersalesGrpcEndpoint extends AftersalesServiceGrpc.AftersalesServiceImplBase {

    private final AftersalesService aftersalesService;

    public AftersalesGrpcEndpoint(AftersalesService aftersalesService) {

        this.aftersalesService = aftersalesService;
    }

    @Override
    public void queryWarranty(QueryWarrantyRequest request, StreamObserver<QueryWarrantyResponse> observer) {
        try {
            WarrantyInfo info = aftersalesService.queryWarranty(request.getOrderId());


            observer.onNext(QueryWarrantyResponse.newBuilder().setSuccess(true).setMessage("success")
                            .setInfo(
                                    com.shangui.userhelp.rpc.WarrantyInfo.newBuilder().setOrderId(info.orderId())
                                    .setWarrantyStatus(info.warrantyStatus())
                                    .setWarrantyUntil(info.warrantyUntil()).build()).build()
            );


        } catch (RuntimeException exception) {

                    observer.onNext(QueryWarrantyResponse.newBuilder().setSuccess(false)
                    .setErrorCode("BUSINESS_ERROR").setMessage(exception.getMessage()).build());
        }
        observer.onCompleted();
    }

    @Override
    public void queryReturnStatus(
            QueryReturnStatusRequest request,
            StreamObserver<QueryReturnStatusResponse> observer
    ) {
        try {
            ReturnInfo info = aftersalesService.queryReturnStatus(request.getOrderId());

            observer.onNext(QueryReturnStatusResponse.newBuilder().setSuccess(true).setMessage("success")
                    .setInfo(com.shangui.userhelp.rpc.ReturnInfo.newBuilder()
                            .setOrderId(info.orderId()).setReturnStatus(info.returnStatus())
                            .setUpdatedAt(info.updatedAt()).build()).build());

        } catch (RuntimeException exception) {

            observer.onNext(QueryReturnStatusResponse.newBuilder().setSuccess(false)
                    .setErrorCode("BUSINESS_ERROR").setMessage(exception.getMessage()).build());
        }
        observer.onCompleted();
    }
}
