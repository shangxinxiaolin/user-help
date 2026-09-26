package com.shangui.userhelp.rpc;

import com.shangui.userhelp.refund.domain.Refund;
import com.shangui.userhelp.refund.service.RefundService;
import io.grpc.stub.StreamObserver;
import net.devh.boot.grpc.server.service.GrpcService;

@GrpcService
public class RefundGrpcEndpoint extends RefundServiceGrpc.RefundServiceImplBase {

    private final RefundService refundService;

    public RefundGrpcEndpoint(RefundService refundService) {
        this.refundService = refundService;
    }

    @Override
    public void validateRefund(ValidateRefundRequest request,
                               StreamObserver<ValidateRefundResponse> observer) {
        try {
            boolean refundable = refundService.validate(request.getContext().getUserId(), request.getOrderId());
            observer.onNext(ValidateRefundResponse.newBuilder().setSuccess(true)
                    .setRefundable(refundable).setMessage("success")
                    .setReason(refundable ? "订单允许退款" : "当前订单状态不允许退款").build());
        } catch (RuntimeException exception) {
            observer.onNext(ValidateRefundResponse.newBuilder().setSuccess(false)
                    .setErrorCode("BUSINESS_ERROR").setMessage(exception.getMessage()).build());
        }
        observer.onCompleted();
    }

    @Override
    public void submitRefund(SubmitRefundRequest request, StreamObserver<SubmitRefundResponse> observer) {
        try {
            Refund refund = refundService.submit(request.getContext().getUserId(), request.getOrderId(),
                    request.getReason(), request.getIdempotencyKey());
            observer.onNext(SubmitRefundResponse.newBuilder().setSuccess(true).setMessage("success")
                    .setRefundId(refund.refundId()).build());
        } catch (RuntimeException exception) {
            observer.onNext(SubmitRefundResponse.newBuilder().setSuccess(false)
                    .setErrorCode("BUSINESS_ERROR").setMessage(exception.getMessage()).build());
        }
        observer.onCompleted();
    }
}
