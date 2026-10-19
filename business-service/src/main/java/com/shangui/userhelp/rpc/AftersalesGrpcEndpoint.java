package com.shangui.userhelp.rpc;

import com.shangui.userhelp.aftersales.service.AftersalesService;
import com.shangui.userhelp.common.error.RpcErrorMapper;
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
            var info = aftersalesService.queryWarranty(request.getOrderId());
            observer.onNext(QueryWarrantyResponse.newBuilder().setSuccess(true).setMessage("success")
                    .setInfo(toProto(info)).build());
        } catch (RuntimeException exception) {
            observer.onNext(QueryWarrantyResponse.newBuilder().setSuccess(false)
                    .setErrorCode(RpcErrorMapper.mapGenericError(exception))
                    .setMessage(exception.getMessage()).build());
        }
        observer.onCompleted();
    }

    @Override
    public void queryReturnStatus(
            QueryReturnStatusRequest request,
            StreamObserver<QueryReturnStatusResponse> observer
    ) {
        try {
            var info = aftersalesService.queryReturnStatus(request.getOrderId());
            observer.onNext(QueryReturnStatusResponse.newBuilder().setSuccess(true).setMessage("success")
                    .setInfo(toProto(info)).build());
        } catch (RuntimeException exception) {
            observer.onNext(QueryReturnStatusResponse.newBuilder().setSuccess(false)
                    .setErrorCode(RpcErrorMapper.mapGenericError(exception))
                    .setMessage(exception.getMessage()).build());
        }
        observer.onCompleted();
    }

    private WarrantyInfo toProto(com.shangui.userhelp.aftersales.domain.WarrantyInfo info) {
        return WarrantyInfo.newBuilder()
                .setOrderId(info.orderId())
                .setWarrantyStatus(info.warrantyStatus())
                .setWarrantyUntil(info.warrantyUntil())
                .build();
    }

    private ReturnInfo toProto(com.shangui.userhelp.aftersales.domain.ReturnInfo info) {
        return ReturnInfo.newBuilder()
                .setOrderId(info.orderId())
                .setReturnStatus(info.returnStatus())
                .setUpdatedAt(info.updatedAt())
                .build();
    }
}
