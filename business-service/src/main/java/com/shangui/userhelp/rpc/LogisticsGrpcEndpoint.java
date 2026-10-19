package com.shangui.userhelp.rpc;

import com.shangui.userhelp.common.error.RpcErrorMapper;
import com.shangui.userhelp.logistics.service.LogisticsService;
import io.grpc.stub.StreamObserver;
import net.devh.boot.grpc.server.service.GrpcService;

@GrpcService
public class LogisticsGrpcEndpoint extends LogisticsServiceGrpc.LogisticsServiceImplBase {

    private final LogisticsService logisticsService;

    public LogisticsGrpcEndpoint(LogisticsService logisticsService) {
        this.logisticsService = logisticsService;
    }

    @Override
    public void queryLogistics(QueryLogisticsRequest request, StreamObserver<QueryLogisticsResponse> observer) {
        try {
            var info = logisticsService.query(request.getTrackingNo());
            observer.onNext(QueryLogisticsResponse.newBuilder().setSuccess(true).setMessage("success")
                    .setInfo(toProto(info)).build());
        } catch (RuntimeException exception) {
            observer.onNext(QueryLogisticsResponse.newBuilder().setSuccess(false)
                    .setErrorCode(RpcErrorMapper.mapGenericError(exception))
                    .setMessage(exception.getMessage()).build());
        }
        observer.onCompleted();
    }

    private LogisticsInfo toProto(com.shangui.userhelp.logistics.domain.LogisticsInfo info) {
        return LogisticsInfo.newBuilder()
                .setTrackingNo(info.trackingNo())
                .setStatus(info.status())
                .setCurrentCity(info.currentCity())
                .addAllTrace(info.trace())
                .build();
    }
}
